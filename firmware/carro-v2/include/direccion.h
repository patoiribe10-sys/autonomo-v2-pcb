#pragma once
#include "tipos.h"

void direccion_init(Direccion *d);                    // adjunta el servo, arranca centrado
int  direccion_pct_a_us(int pct);                     // -100..100 -> 1190..1730 us
int  direccion_us_a_pct(int us);                      // al reves
void direccion_fijar_porcentaje(Direccion *d, int pct);
void direccion_centrar(Direccion *d);
void direccion_actualizar(Direccion *d, uint32_t ahora_ms);  // movimiento suave
int  direccion_pct_actual(const Direccion *d);
