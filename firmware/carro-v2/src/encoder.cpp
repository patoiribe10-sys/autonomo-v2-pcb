#include "encoder.h"
#include "pines_v2.h"
#include "driver/gpio.h"

// La ISR no recibe argumentos, asi que guardamos el apuntador aqui
static Encoder *s_enc = NULL;
static portMUX_TYPE s_mux = portMUX_INITIALIZER_UNLOCKED;

// Misma logica del repo (prueba-pcb): en cada flanco de A, si A esta en alto
// se mira B. B alto = -1, B bajo = +1. Con esta ISR, en la placa real adelante
// cuenta NEGATIVO (probado el 25-nov-2026). Por eso ENC_SIGNO = -1 en config.h:
// lo deja positivo hacia adelante. No cambiar uno sin el otro.
static void IRAM_ATTR encoder_isr(void) {
  if (s_enc == NULL) return;
  if (gpio_get_level((gpio_num_t)s_enc->pin_a)) {
    portENTER_CRITICAL_ISR(&s_mux);
    if (gpio_get_level((gpio_num_t)s_enc->pin_b)) s_enc->cuenta -= 1;
    else                                          s_enc->cuenta += 1;
    portEXIT_CRITICAL_ISR(&s_mux);
  }
}

void encoder_init(Encoder *e) {
  e->pin_a = PIN_ENC_A;
  e->pin_b = PIN_ENC_B;
  e->cuenta = 0;
  e->cuenta_previa = 0;
  e->t_previo_ms = millis();
  e->pulsos_s = 0;
  pinMode(e->pin_a, INPUT);                       // GPIO34/35 no tienen pull interno (la placa trae R14/R15)
  pinMode(e->pin_b, INPUT);
  s_enc = e;
  attachInterrupt(digitalPinToInterrupt(e->pin_a), encoder_isr, CHANGE);
}

int32_t encoder_leer_cuenta(Encoder *e) {
  portENTER_CRITICAL(&s_mux);
  int32_t c = e->cuenta;
  portEXIT_CRITICAL(&s_mux);
  return c;
}

void encoder_actualizar(Encoder *e, uint32_t ahora_ms) {
  uint32_t dt = ahora_ms - e->t_previo_ms;
  if (dt < ENC_VENTANA_MS) return;
  int32_t c = encoder_leer_cuenta(e);
  int32_t delta = c - e->cuenta_previa;
  e->pulsos_s = ENC_SIGNO * (int)((int64_t)delta * 1000 / (int32_t)dt);
  e->cuenta_previa = c;
  e->t_previo_ms = ahora_ms;
}
