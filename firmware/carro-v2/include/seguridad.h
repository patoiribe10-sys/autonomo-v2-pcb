#pragma once
#include "tipos.h"

// Botones
void boton_init(Boton *b, uint8_t pin);
bool boton_actualizar(Boton *b, uint32_t ahora_ms);   // true solo en el instante en que se presiona

// Bateria
void bateria_init(Bateria *b);
void bateria_actualizar(Bateria *b, uint32_t ahora_ms);
int  bateria_mv_reportado(const Bateria *b);          // 0 si solo hay USB

// Paro de emergencia
void paro_init(Paro *p);
void paro_actualizar(Paro *p, uint32_t ahora_ms);
bool paro_activo(const Paro *p);                      // hw o sw
