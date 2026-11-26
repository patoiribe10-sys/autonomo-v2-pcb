#include "seguridad.h"
#include "pines_v2.h"

// ---------------- Botones ----------------
void boton_init(Boton *b, uint8_t pin) {
  b->pin = pin;
  b->pulsado = false;
  b->lectura_previa = false;
  b->t_cambio_ms = 0;
}

bool boton_actualizar(Boton *b, uint32_t ahora_ms) {
  bool lectura = (digitalRead(b->pin) == LOW);        // LOW = presionado
  if (lectura != b->lectura_previa) {
    b->lectura_previa = lectura;
    b->t_cambio_ms = ahora_ms;
  }
  if (lectura != b->pulsado && ahora_ms - b->t_cambio_ms >= BOTON_REBOTE_MS) {
    b->pulsado = lectura;
    return lectura;                                    // flanco de bajada = recien presionado
  }
  return false;
}

// ---------------- Bateria ----------------
void bateria_init(Bateria *b) {
  memset(b, 0, sizeof(*b));
}

static int leer_bateria_mv(void) {
  // lectura en el pin (mV) por el factor del divisor 100k/22k
  return (int)(analogReadMilliVolts(PIN_VBAT_SENSE) * VBAT_DIVISOR);
}

void bateria_actualizar(Bateria *b, uint32_t ahora_ms) {
  if (b->inicializada && ahora_ms - b->t_muestra_ms < BAT_MUESTREO_MS) return;
  b->t_muestra_ms = ahora_ms;

  int mv = leer_bateria_mv();
  if (!b->inicializada) {                             // primera lectura: llena todo el buffer
    for (int i = 0; i < BAT_N_MUESTRAS; i++) b->muestras[i] = mv;
    b->suma = (uint32_t)mv * BAT_N_MUESTRAS;
    b->inicializada = true;
  } else {
    b->suma -= b->muestras[b->idx];
    b->muestras[b->idx] = mv;
    b->suma += mv;
    b->idx = (b->idx + 1) % BAT_N_MUESTRAS;
  }
  b->mv = (int)(b->suma / BAT_N_MUESTRAS);

  // Solo USB: no es bateria baja, simplemente no hay bateria
  b->presente = (b->mv >= BAT_SIN_BATERIA_MV);
  if (!b->presente) {
    b->baja = b->critica = false;
    b->cont_baja = b->cont_critica = false;
    return;
  }

  // Baja: < 10.5 V por 2 s. Se quita con histeresis (> 10.8 V)
  if (b->mv < BAT_BAJA_MV) {
    if (!b->cont_baja) { b->cont_baja = true; b->t_baja_ms = ahora_ms; }
    if (ahora_ms - b->t_baja_ms >= BAT_BAJA_T_MS) b->baja = true;
  } else if (b->mv > BAT_RECUPERA_MV) {
    b->cont_baja = false;
    b->baja = false;
  } else if (!b->baja) {
    b->cont_baja = false;                              // en la zona de histeresis no se acumula tiempo
  }

  // Critica: < 9.9 V por 1 s. Se queda hasta que suba de 10.8 V
  if (b->mv < BAT_CRITICA_MV) {
    if (!b->cont_critica) { b->cont_critica = true; b->t_critica_ms = ahora_ms; }
    if (ahora_ms - b->t_critica_ms >= BAT_CRITICA_T_MS) b->critica = true;
  } else {
    b->cont_critica = false;
    if (b->mv > BAT_RECUPERA_MV) b->critica = false;
  }
}

int bateria_mv_reportado(const Bateria *b) {
  return b->presente ? b->mv : 0;
}

// ---------------- Paro de emergencia ----------------
void paro_init(Paro *p) {
  memset(p, 0, sizeof(*p));
  boton_init(&p->boot, PIN_BOOT);
  boton_init(&p->start, PIN_START);
}

// Misma logica del demo y de prueba-pcb: ESTOP_G se lee por ADC con el divisor
// 100k/22k. Si el voltaje calculado es > 5 V el lazo de J10 esta abierto
// (ESTOP_G ~ VBAT) y el paro esta ACTIVO. Con el lazo cerrado queda cerca de 0 V.
static bool lectura_estop_activa(Paro *p) {
  p->mv_estop = (int)(analogReadMilliVolts(PIN_ESTOP_SENSE) * VBAT_DIVISOR);
  return p->mv_estop > (int)(ESTOP_UMBRAL_V * 1000.0f);
}

void paro_actualizar(Paro *p, uint32_t ahora_ms) {
  // Botones: BOOT = paro por software, START lo libera
  if (boton_actualizar(&p->boot, ahora_ms)) p->sw = true;
  if (boton_actualizar(&p->start, ahora_ms) && p->sw && !p->boot.pulsado) p->sw = false;

  if (ahora_ms - p->t_muestra_ms < ESTOP_MUESTREO_MS) return;
  p->t_muestra_ms = ahora_ms;

  // Antirrebote por conteo: 2 lecturas seguidas para activar, 5 para liberar
  if (lectura_estop_activa(p)) {
    p->cuenta_off = 0;
    if (p->cuenta_on < 255) p->cuenta_on++;
    if (p->cuenta_on >= ESTOP_CONF_ON) p->hw = true;
  } else {
    p->cuenta_on = 0;
    if (p->cuenta_off < 255) p->cuenta_off++;
    if (p->cuenta_off >= ESTOP_CONF_OFF) p->hw = false;
  }
}

bool paro_activo(const Paro *p) {
  return p->hw || p->sw;
}
