#pragma once
#include "tipos.h"

void carro_init(Carro *c);   // pines, servo, motor, encoder, puertos serie
void carro_paso(Carro *c);   // un ciclo del loop (sin delays largos)
