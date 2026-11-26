#pragma once
#include "tipos.h"

void    encoder_init(Encoder *e);                       // pines e interrupcion
int32_t encoder_leer_cuenta(Encoder *e);                // lectura con seccion critica
void    encoder_actualizar(Encoder *e, uint32_t ahora_ms);  // calcula pulsos/s cada 50 ms
