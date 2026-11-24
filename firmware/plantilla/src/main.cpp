// Programa base: parpadea el LED HB y lee la bateria.
#include <Arduino.h>
#include "pines_v2.h"

void setup() {
  Serial.begin(115200);
  pinMode(PIN_LED_HB, OUTPUT);
  pinMode(PIN_MOT_STBY, OUTPUT);
  digitalWrite(PIN_MOT_STBY, LOW);   // motor apagado al arrancar
  analogSetAttenuation(ADC_11db);
  Serial.println("Plantilla PCB Autonomo_V2 lista");
}

void loop() {
  digitalWrite(PIN_LED_HB, !digitalRead(PIN_LED_HB));
  float vbat = analogReadMilliVolts(PIN_VBAT_SENSE) / 1000.0f * VBAT_DIVISOR;
  Serial.printf("VBAT = %.2f V\n", vbat);   // con solo USB marca ~0 V
  delay(1000);
}
