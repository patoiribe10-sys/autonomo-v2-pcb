#include "protocolo.h"
#include <stdlib.h>
#include <stdio.h>
#include <ctype.h>

static const char *saltar_espacios(const char *p) {
  while (*p == ' ' || *p == '\t') p++;
  return p;
}

// Lee un entero decimal con signo y lo recorta a -100..100.
// Regresa false si no hay ningun digito.
static bool leer_entero(const char **p, int *salida) {
  char *fin;
  long v = strtol(*p, &fin, 10);
  if (fin == *p) return false;
  if (v > 100) v = 100;
  if (v < -100) v = -100;
  *salida = (int)v;
  *p = fin;
  return true;
}

TipoLinea protocolo_procesar_linea(const char *linea, Comando *c) {
  const char *p = saltar_espacios(linea);

  if (*p == 'P' && *saltar_espacios(p + 1) == '\0') return LINEA_PING;
  if (*p == '?' && *saltar_espacios(p + 1) == '\0') return LINEA_ESTADO;

  // V<vel>,S<dir>
  if (*p != 'V') return LINEA_INVALIDA;
  p++;
  int vel, dir;
  if (!leer_entero(&p, &vel)) return LINEA_INVALIDA;
  p = saltar_espacios(p);
  if (*p != ',') return LINEA_INVALIDA;
  p = saltar_espacios(p + 1);
  if (*p != 'S') return LINEA_INVALIDA;
  p++;
  if (!leer_entero(&p, &dir)) return LINEA_INVALIDA;
  if (*saltar_espacios(p) != '\0') return LINEA_INVALIDA;   // basura al final

  c->vel = vel;
  c->dir = dir;
  return LINEA_MANDO;
}

int protocolo_telemetria(char *salida, size_t max, int vel, int dir, int mv, int estado) {
  return snprintf(salida, max, "v%d,s%d,b%d,e%d\n", vel, dir, mv, estado);
}
