#include "tipos.h"
#include "direccion.h"
#include "protocolo.h"
#include <stdio.h>
static int fallas = 0, total = 0;
#define CHECK(nombre, cond) do { total++; if (cond) printf("[OK ] %s\n", nombre); else { fallas++; printf("[FALLA] %s\n", nombre); } } while (0)
int main() {
  // ---- servo: porcentaje -> microsegundos (S+ = derecha = 1680)
  CHECK("S=+100  -> 1680 us (derecha total)",  direccion_pct_a_us(100)  == 1680);
  CHECK("S=0     -> 1360 us (centro)",         direccion_pct_a_us(0)    == 1360);
  CHECK("S=-100  -> 1190 us (izquierda total)", direccion_pct_a_us(-100) == 1190);
  CHECK("S=+50   -> 1520 us",                  direccion_pct_a_us(50)   == 1520);
  CHECK("S=-50   -> 1275 us",                  direccion_pct_a_us(-50)  == 1275);
  CHECK("S=+999  se recorta a 1680 (nunca mas)", direccion_pct_a_us(999)  == 1680);
  CHECK("S=-999  se recorta a 1190 (nunca 1100)", direccion_pct_a_us(-999) == 1190);
  for (int p = -100; p <= 100; p++) { int us = direccion_pct_a_us(p); if (us < 1190 || us > 1680) { CHECK("rango 1190..1680 para todo S", false); return 1; } }
  CHECK("para todo S de -100 a 100 el servo queda en 1190..1680 (nunca 1100)", true);
  // ---- protocolo: lineas validas e invalidas
  Comando c; memset(&c, 0, sizeof(c)); c.vel = 7; c.dir = 9;
  struct { const char *l; TipoLinea t; int vel, dir; } casos[] = {
    {"V30,S100", LINEA_MANDO, 30, 100}, {"V-100,S-100", LINEA_MANDO, -100, -100}, {"V0,S0", LINEA_MANDO, 0, 0},
    {"V500,S-900", LINEA_MANDO, 100, -100}, {"V+30,S+10", LINEA_MANDO, 30, 10}, {"  V 30 , S 40 ", LINEA_MANDO, 30, 40},
    {"P", LINEA_PING, 0, 0}, {"P  ", LINEA_PING, 0, 0}, {"?", LINEA_ESTADO, 0, 0},
    {"V5.5,S0", LINEA_INVALIDA, 0, 0}, {"V30", LINEA_INVALIDA, 0, 0}, {"V30,S", LINEA_INVALIDA, 0, 0}, {"V,S", LINEA_INVALIDA, 0, 0},
    {"S30,V10", LINEA_INVALIDA, 0, 0}, {"V30,S10x", LINEA_INVALIDA, 0, 0}, {"", LINEA_INVALIDA, 0, 0}, {"v30,s10", LINEA_INVALIDA, 0, 0},
    {"PP", LINEA_INVALIDA, 0, 0}, {"V30;S10", LINEA_INVALIDA, 0, 0}, {"hola", LINEA_INVALIDA, 0, 0}, {"V30,S10,X5", LINEA_INVALIDA, 0, 0},
  };
  for (unsigned i = 0; i < sizeof(casos) / sizeof(casos[0]); i++) {
    Comando k; memset(&k, 0, sizeof(k)); k.vel = 7; k.dir = 9;
    TipoLinea t = protocolo_procesar_linea(casos[i].l, &k);
    bool ok = (t == casos[i].t);
    if (t == LINEA_MANDO) ok = ok && k.vel == casos[i].vel && k.dir == casos[i].dir;
    else ok = ok && k.vel == 7 && k.dir == 9;            // una linea que no es mando NO toca el comando previo
    char nombre[160]; snprintf(nombre, sizeof(nombre), "linea \"%s\" -> %s", casos[i].l,
      casos[i].t == LINEA_MANDO ? "mando" : casos[i].t == LINEA_PING ? "ping" : casos[i].t == LINEA_ESTADO ? "estado" : "ignorada, sin tocar el comando");
    CHECK(nombre, ok);
  }
  // ---- telemetria: formato y recorte de buffer
  char s[48];
  int n = protocolo_telemetria(s, sizeof(s), 120, -10, 11800, 0);
  CHECK("telemetria con valores normales = \"v120,s-10,b11800,e0\\n\"", n == (int)strlen(s) && strcmp(s, "v120,s-10,b11800,e0\n") == 0);
  n = protocolo_telemetria(s, sizeof(s), -2147483647, -100, 65535, 3);
  CHECK("la telemetria mas larga posible cabe en el buffer de 48", n > 0 && n < (int)sizeof(s));
  char chico[8]; n = protocolo_telemetria(chico, sizeof(chico), 120, -10, 11800, 0);
  CHECK("buffer chico: devuelve n >= tamano (por eso carro.cpp ya no manda la linea cortada)", n >= (int)sizeof(chico));
  // lineas de telemetria para que Python las pase por el regex del puente
  const int vs[] = {0, 120, -300, 2147483647, -2147483647}; const int ds[] = {-100, 0, 100}; const int ms[] = {0, 9900, 11800, 12600};
  FILE *f = fopen("telemetria.txt", "w");
  for (int a : vs) for (int b : ds) for (int m : ms) for (int e = 0; e <= 3; e++) { protocolo_telemetria(s, sizeof(s), a, b, m, e); fputs(s, f); }
  fclose(f);
  printf("\n%d de %d comprobaciones OK\n", total - fallas, total);
  return fallas ? 1 : 0;
}
