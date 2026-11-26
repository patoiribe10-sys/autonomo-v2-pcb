#include "carro.h"
#include "pines_v2.h"
#include "motor.h"
#include "direccion.h"
#include "encoder.h"
#include "protocolo.h"
#include "seguridad.h"

// ---------------- Utilidades de puerto ----------------
static void enviar(Stream *p, const char *texto) {
  p->write((const uint8_t *)texto, strlen(texto));
}

static void enviar_estado_legible(Carro *c, Stream *p) {
  char s[200];
  snprintf(s, sizeof(s),
           "estado=%d timeout=%d paro_hw=%d paro_sw=%d bat=%dmV(%s) estop=%dmV "
           "cmd=V%d,S%d pwm=%d dir_us=%d enc=%d pps\n",
           c->estado, c->timeout, c->paro.hw, c->paro.sw, c->bat.mv,
           !c->bat.presente ? "sin bateria" : c->bat.critica ? "critica" : c->bat.baja ? "baja" : "ok",
           c->paro.mv_estop, c->cmd.vel, c->cmd.dir, c->motor.pwm_actual,
           (int)(c->dir.us_actual + 0.5f), c->enc.pulsos_s);
  enviar(p, s);
}

// ---------------- Recepcion ----------------
static void atender_linea(Carro *c, LineaRx *rx, uint32_t ahora_ms) {
  rx->buf[rx->n] = '\0';
  if (rx->n > 0 && rx->buf[rx->n - 1] == '\r') rx->buf[rx->n - 1] = '\0';

  TipoLinea t = protocolo_procesar_linea(rx->buf, &c->cmd);
  if (t == LINEA_INVALIDA) return;

  c->cmd.puerto = rx->puerto;                // contestamos por donde llego el ultimo valido
  if (t == LINEA_MANDO) {
    c->cmd.t_ultimo_ms = ahora_ms;           // solo V/S reinician el timeout
    c->cmd.recibido = true;
  } else if (t == LINEA_PING) {
    enviar(rx->puerto, "pong\n");
  } else if (t == LINEA_ESTADO) {
    enviar_estado_legible(c, rx->puerto);
  }
}

static void leer_puerto(Carro *c, LineaRx *rx, uint32_t ahora_ms) {
  while (rx->puerto->available() > 0) {
    int b = rx->puerto->read();
    if (b < 0) break;
    if (b == '\n') {
      if (!rx->desbordado) atender_linea(c, rx, ahora_ms);
      rx->n = 0;
      rx->desbordado = false;
    } else if (rx->n < LINEA_MAX - 1) {
      rx->buf[rx->n++] = (char)b;
    } else {
      rx->desbordado = true;                 // muy larga: se tira completa
    }
  }
}

// ---------------- Indicadores ----------------
static void indicadores(Carro *c, uint32_t ahora_ms) {
  // LED HB: 1 Hz si todo bien, rapido si paro / timeout / bateria critica
  bool falla = (c->estado == ESTADO_PARO || c->estado == ESTADO_TIMEOUT || c->bat.critica);
  uint32_t medio = falla ? LED_FALLA_MS : LED_OK_MS;
  if (ahora_ms - c->t_led_ms >= medio) {
    c->t_led_ms = ahora_ms;
    c->led = !c->led;
    digitalWrite(PIN_LED_HB, c->led);
  }

  // Buzzer intermitente con bateria baja (no con solo USB)
  if (c->bat.presente && (c->bat.baja || c->bat.critica)) {
    uint32_t espera = c->buzzer ? BUZZER_ON_MS : BUZZER_OFF_MS;
    if (ahora_ms - c->t_buzzer_ms >= espera) {
      c->t_buzzer_ms = ahora_ms;
      c->buzzer = !c->buzzer;
      digitalWrite(PIN_BUZZER, c->buzzer);
    }
  } else if (c->buzzer) {
    c->buzzer = false;
    digitalWrite(PIN_BUZZER, LOW);
  }
}

// ---------------- Init ----------------
void carro_init(Carro *c) {
  memset(c, 0, sizeof(*c));

  Serial.begin(BAUDIOS);
  Serial2.begin(BAUDIOS, SERIAL_8N1, PIN_UART2_RX, PIN_UART2_TX);
  c->rx_usb.puerto = &Serial;
  c->rx_uart2.puerto = &Serial2;
  c->cmd.puerto = &Serial;                   // hasta que llegue un comando, USB

  pinMode(PIN_LED_HB, OUTPUT);
  pinMode(PIN_BUZZER, OUTPUT);
  digitalWrite(PIN_BUZZER, LOW);
  pinMode(PIN_START, INPUT);                 // pull-up externo R37
  pinMode(PIN_BOOT, INPUT_PULLUP);           // BOOT (S2)
  analogSetAttenuation(ADC_11db);

  ESP32PWM::allocateTimer(0);                // servo primero, luego el PWM del motor
  direccion_init(&c->dir);
  motor_init(&c->motor);
  encoder_init(&c->enc);
  bateria_init(&c->bat);
  paro_init(&c->paro);

  c->estado = ESTADO_TIMEOUT;                // sin comandos todavia
  c->timeout = true;
}

// ---------------- Ciclo ----------------
void carro_paso(Carro *c) {
  uint32_t ahora = millis();

  // 1) Sensores y seguridad
  paro_actualizar(&c->paro, ahora);
  bateria_actualizar(&c->bat, ahora);
  encoder_actualizar(&c->enc, ahora);

  // 2) Comandos de la Jetson (USB y UART2)
  leer_puerto(c, &c->rx_usb, ahora);
  leer_puerto(c, &c->rx_uart2, ahora);

  // 3) Decidir estado (prioridad: paro, bateria critica, timeout, bateria baja)
  c->timeout = !c->cmd.recibido || (ahora - c->cmd.t_ultimo_ms > TIMEOUT_CMD_MS);
  bool paro = paro_activo(&c->paro);
  if (paro)                     c->estado = ESTADO_PARO;
  else if (c->bat.critica)      c->estado = ESTADO_BAT_BAJA;
  else if (c->timeout)          c->estado = ESTADO_TIMEOUT;
  else if (c->bat.baja)         c->estado = ESTADO_BAT_BAJA;
  else                          c->estado = ESTADO_OK;

  // 4) Aplicar
  if (paro) {
    motor_parar_ya(&c->motor);               // inmediato, sin rampa
  } else if (c->bat.critica || c->timeout) {
    motor_fijar_velocidad(&c->motor, 0, 100);  // frena con la rampa
  } else {
    int limite = c->bat.baja ? BAT_VEL_MAX_BAJA : 100;
    motor_fijar_velocidad(&c->motor, c->cmd.vel, limite);
  }
  if (c->timeout) direccion_centrar(&c->dir);
  else            direccion_fijar_porcentaje(&c->dir, c->cmd.dir);

  motor_actualizar(&c->motor, ahora);
  direccion_actualizar(&c->dir, ahora);

  // 5) Telemetria a 20 Hz por el puerto del ultimo comando valido
  if (ahora - c->t_telem_ms >= TELEMETRIA_MS) {
    c->t_telem_ms = ahora;
    char s[48];
    int n = protocolo_telemetria(s, sizeof(s), c->enc.pulsos_s, direccion_pct_actual(&c->dir),
                                 bateria_mv_reportado(&c->bat), c->estado);
    if (n > 0) c->cmd.puerto->write((const uint8_t *)s, n);
  }

  indicadores(c, ahora);
}
