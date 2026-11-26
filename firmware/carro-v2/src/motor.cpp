#include "motor.h"
#include "pines_v2.h"

static int signo(int x) { return (x > 0) - (x < 0); }

void motor_init(Motor *m) {
  m->pin_pwm = PIN_MOT_PWM;
  m->pin_in1 = PIN_MOT_IN1;
  m->pin_in2 = PIN_MOT_IN2;
  m->pin_stby = PIN_MOT_STBY;
  m->pwm_actual = 0;
  m->pwm_objetivo = 0;
  m->t_rampa_ms = 0;

  pinMode(m->pin_in1, OUTPUT);
  pinMode(m->pin_in2, OUTPUT);
  pinMode(m->pin_stby, OUTPUT);
  digitalWrite(m->pin_stby, HIGH);               // habilitado desde el inicio
  // OJO: ESP32PWM::allocateTimer(0) ya se llamo en carro_init, antes del servo
  ledcAttach(m->pin_pwm, MOTOR_PWM_HZ, MOTOR_PWM_BITS);
  motor_aplicar(m, 0);
}

void motor_aplicar(Motor *m, int pwm) {          // positivo = adelante
  pwm *= DIR_ADELANTE;
  digitalWrite(m->pin_in1, pwm > 0);
  digitalWrite(m->pin_in2, pwm < 0);
  ledcWrite(m->pin_pwm, constrain(abs(pwm), 0, PWM_MAX));
}

// vel_pct -100..100 -> PWM con zona muerta: 1% = PWM_MIN_ARRANQUE, 100% = PWM_MAX
void motor_fijar_velocidad(Motor *m, int vel_pct, int limite_pct) {
  int v = constrain(vel_pct, -limite_pct, limite_pct);
  if (v == 0) { m->pwm_objetivo = 0; return; }
  int mag = abs(v);
  int pwm = PWM_MIN_ARRANQUE + (mag - 1) * (PWM_MAX - PWM_MIN_ARRANQUE) / 99;
  m->pwm_objetivo = signo(v) * pwm;
}

void motor_actualizar(Motor *m, uint32_t ahora_ms) {
  if (ahora_ms - m->t_rampa_ms < RAMPA_PASO_MS) return;
  m->t_rampa_ms = ahora_ms;
  if (m->pwm_actual == m->pwm_objetivo) return;

  int dif = m->pwm_objetivo - m->pwm_actual;
  int sig = constrain(m->pwm_actual + constrain(dif, -RAMPA_PWM_PASO, RAMPA_PWM_PASO), -PWM_MAX, PWM_MAX);

  // Zona muerta: no nos quedamos en valores que no mueven el motor
  if (sig != 0 && abs(sig) < PWM_MIN_ARRANQUE) {
    if (m->pwm_objetivo == 0 || signo(m->pwm_objetivo) != signo(sig)) sig = 0;
    else sig = signo(sig) * PWM_MIN_ARRANQUE;
  }
  // Saliendo de cero hacia un objetivo: arranca directo en el minimo
  if (m->pwm_actual == 0 && m->pwm_objetivo != 0 && sig == 0) sig = signo(m->pwm_objetivo) * PWM_MIN_ARRANQUE;

  m->pwm_actual = sig;
  motor_aplicar(m, sig);
}

void motor_parar_ya(Motor *m) {
  m->pwm_objetivo = 0;
  m->pwm_actual = 0;
  motor_aplicar(m, 0);
}
