#pragma once
#include "tipos.h"

void motor_init(Motor *m);                       // pines, STBY en HIGH, PWM de 8 bits
void motor_aplicar(Motor *m, int pwm);           // escribe directo al puente H (-255..255)
void motor_fijar_velocidad(Motor *m, int vel_pct, int limite_pct);  // pone el objetivo
void motor_actualizar(Motor *m, uint32_t ahora_ms);  // da los pasos de la rampa
void motor_parar_ya(Motor *m);                   // a cero sin rampa
