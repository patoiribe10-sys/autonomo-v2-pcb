/*
 * Firmware del carro autonomo RoboUAQ 2026 - PCB Autonomo_V2
 *
 * Recibe "V<vel>,S<dir>" de la Jetson (USB o UART2) y manda
 * "v<pulsos/s>,s<dir>,b<mV>,e<estado>" a 20 Hz. Detalles en README.md.
 * Toda la logica esta en los modulos de src/ (motor, direccion, encoder,
 * protocolo, seguridad y carro).
 */
#include <Arduino.h>
#include "carro.h"

static Carro carro;

void setup() {
  carro_init(&carro);
}

void loop() {
  carro_paso(&carro);
  delay(1);   // cede CPU; los tiempos van todos con millis()
}
