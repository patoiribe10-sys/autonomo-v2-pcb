#include "direccion.h"
#include "pines_v2.h"

// Interpolacion separada a cada lado del centro (el servo no es simetrico)
int direccion_pct_a_us(int pct) {
  pct = constrain(pct, -100, 100);
  if (pct < 0) return SERVO_CENTRO + pct * (SERVO_CENTRO - SERVO_MIN) / 100;
  return SERVO_CENTRO + pct * (SERVO_MAX - SERVO_CENTRO) / 100;
}

int direccion_us_a_pct(int us) {
  us = constrain(us, SERVO_MIN, SERVO_MAX);
  if (us < SERVO_CENTRO) return (us - SERVO_CENTRO) * 100 / (SERVO_CENTRO - SERVO_MIN);
  return (us - SERVO_CENTRO) * 100 / (SERVO_MAX - SERVO_CENTRO);
}

// Unico lugar donde se escribe al servo: aqui se recorta SIEMPRE al rango
static void escribir_us(Direccion *d, int us) {
  us = constrain(us, SERVO_MIN, SERVO_MAX);
  if (us == d->us_escrito) return;
  d->us_escrito = us;
  d->servo.writeMicroseconds(us);
}

void direccion_init(Direccion *d) {
  d->pin = PIN_SERVO;
  d->us_actual = SERVO_CENTRO;
  d->us_objetivo = SERVO_CENTRO;
  d->us_escrito = -1;
  d->t_ultimo_ms = millis();
  d->servo.setPeriodHertz(50);
  d->servo.attach(d->pin, 500, 2500);            // igual que el demo
  escribir_us(d, SERVO_CENTRO);
}

void direccion_fijar_porcentaje(Direccion *d, int pct) {
  d->us_objetivo = direccion_pct_a_us(pct);
}

void direccion_centrar(Direccion *d) {
  d->us_objetivo = SERVO_CENTRO;
}

void direccion_actualizar(Direccion *d, uint32_t ahora_ms) {
  uint32_t dt = ahora_ms - d->t_ultimo_ms;
  if (dt == 0) return;
  d->t_ultimo_ms = ahora_ms;

  float paso = SERVO_VEL_US_S * dt / 1000.0f;    // lo maximo que puede moverse en este dt
  float dif = d->us_objetivo - d->us_actual;
  if (dif > paso) dif = paso;
  else if (dif < -paso) dif = -paso;
  d->us_actual += dif;
  escribir_us(d, (int)(d->us_actual + 0.5f));
}

int direccion_pct_actual(const Direccion *d) {
  return direccion_us_a_pct((int)(d->us_actual + 0.5f));
}
