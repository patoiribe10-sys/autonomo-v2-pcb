#pragma once
#include "tipos.h"

// Lo que resulto de procesar una linea
typedef enum {
  LINEA_INVALIDA = 0,   // mal formada: se ignora
  LINEA_MANDO,          // V<vel>,S<dir>: ya quedo en el Comando
  LINEA_PING,           // P
  LINEA_ESTADO          // ?
} TipoLinea;

// Lee una linea (sin el \n). Solo toca c->vel y c->dir si es un mando valido.
TipoLinea protocolo_procesar_linea(const char *linea, Comando *c);

// Arma la linea de telemetria "v<vel>,s<dir>,b<mV>,e<estado>\n"
int protocolo_telemetria(char *salida, size_t max, int vel, int dir, int mv, int estado);
