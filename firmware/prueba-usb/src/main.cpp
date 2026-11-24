/*
 * Prueba USB + botones + LED HB — PCB Autonomo_V2 (RoboUAQ 2026)
 *
 * Solo con el cable USB-C. Abre el monitor serial a 115200.
 *  - Cada segundo manda un "latido" con contador, tiempo y voltaje de bateria.
 *  - Todo lo que escribas en el monitor te lo regresa (eco).
 *  - LED HB: parpadea lento normal, fijo con START, rapido con BOOT.
 *
 * Comandos (escribe la letra y Enter):
 *   ?  ayuda      i  info del chip      l  prende/apaga el LED a mano
 *   p  pausa/reanuda el latido
 */
#include <Arduino.h>

#define PIN_LED_HB      2   // LED HB (D5)
#define PIN_BOOT        0   // boton BOOT (S2), LOW = presionado
#define PIN_START      27   // boton START (S3 y J10.1), LOW = presionado
#define PIN_VBAT_SENSE 36
#define PIN_MOT_STBY   19   // se deja en LOW: motor apagado

const float VBAT_DIVISOR = (100.0f + 22.0f) / 22.0f;

uint32_t contador = 0;
bool latidoActivo = true;
bool ledManual = false;     // true = el LED lo controlas tu con 'l'
bool ledManualEstado = false;
String linea;

void ayuda() {
  Serial.println();
  Serial.println(F("===== PRUEBA USB PCB Autonomo_V2 ====="));
  Serial.println(F(" Escribe algo y Enter: te lo regreso (eco)."));
  Serial.println(F(" ?  ayuda"));
  Serial.println(F(" i  info del chip"));
  Serial.println(F(" l  LED HB a mano (prende/apaga). Otra vez 'l' vuelve a automatico"));
  Serial.println(F(" p  pausa / reanuda el latido"));
  Serial.println(F(" Botones: START = LED fijo | BOOT = LED rapido | EN = reinicia"));
  Serial.println();
}

void info() {
  Serial.println(F("[info]"));
  Serial.printf("  Chip: %s rev %d, %d nucleos a %lu MHz\n", ESP.getChipModel(), ESP.getChipRevision(), ESP.getChipCores(), (unsigned long)ESP.getCpuFreqMHz());
  Serial.printf("  Flash: %lu MB\n", (unsigned long)(ESP.getFlashChipSize() / (1024 * 1024)));
  Serial.printf("  RAM libre: %lu bytes\n", (unsigned long)ESP.getFreeHeap());
  uint64_t mac = ESP.getEfuseMac();
  Serial.printf("  MAC: %02X:%02X:%02X:%02X:%02X:%02X\n",
                (uint8_t)(mac), (uint8_t)(mac >> 8), (uint8_t)(mac >> 16),
                (uint8_t)(mac >> 24), (uint8_t)(mac >> 32), (uint8_t)(mac >> 40));
}

void procesarLinea(String s) {
  s.trim();
  if (s.length() == 0) return;
  if (s == "?") { ayuda(); return; }
  if (s == "i") { info(); return; }
  if (s == "p") { latidoActivo = !latidoActivo; Serial.println(latidoActivo ? F("[latido reanudado]") : F("[latido en pausa]")); return; }
  if (s == "l") {
    if (!ledManual) { ledManual = true; ledManualEstado = true; Serial.println(F("[LED a mano: PRENDIDO]")); }
    else if (ledManualEstado) { ledManualEstado = false; Serial.println(F("[LED a mano: APAGADO]")); }
    else { ledManual = false; Serial.println(F("[LED en automatico]")); }
    return;
  }
  Serial.printf("[eco] Recibi %u caracteres: %s\n", (unsigned)s.length(), s.c_str());
}

void setup() {
  pinMode(PIN_MOT_STBY, OUTPUT); digitalWrite(PIN_MOT_STBY, LOW);
  pinMode(PIN_LED_HB, OUTPUT);
  pinMode(PIN_BOOT, INPUT_PULLUP);
  pinMode(PIN_START, INPUT);           // pull-up externo R37
  analogSetAttenuation(ADC_11db);
  Serial.begin(115200);
  delay(300);
  // saludo con el LED: 3 parpadeos
  for (int i = 0; i < 3; i++) { digitalWrite(PIN_LED_HB, HIGH); delay(120); digitalWrite(PIN_LED_HB, LOW); delay(120); }
  ayuda();
  info();
}

void loop() {
  static uint32_t tLatido = 0;
  static int startPrev = -1, bootPrev = -1;

  // ---- botones ----
  int start = digitalRead(PIN_START) == LOW;
  int boot  = digitalRead(PIN_BOOT)  == LOW;
  if (start != startPrev) { if (startPrev != -1) Serial.println(start ? F(">> START presionado") : F(">> START suelto")); startPrev = start; }
  if (boot  != bootPrev)  { if (bootPrev  != -1) Serial.println(boot  ? F(">> BOOT presionado")  : F(">> BOOT suelto"));  bootPrev  = boot; }

  // ---- LED HB ----
  bool led;
  if (ledManual)  led = ledManualEstado;
  else if (start) led = true;                       // fijo
  else if (boot)  led = (millis() / 80) % 2;        // rapido
  else            led = (millis() / 500) % 2;       // lento
  digitalWrite(PIN_LED_HB, led);

  // ---- latido por USB ----
  if (latidoActivo && millis() - tLatido >= 1000) {
    tLatido = millis();
    float vbat = analogReadMilliVolts(PIN_VBAT_SENSE) / 1000.0f * VBAT_DIVISOR;
    Serial.printf("latido #%lu | %lu s encendido | VBAT %.2f V | START %s | BOOT %s\n",
                  (unsigned long)++contador, (unsigned long)(millis() / 1000), vbat,
                  start ? "presionado" : "suelto", boot ? "presionado" : "suelto");
  }

  // ---- lo que llega de la compu ----
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\n' || c == '\r') { procesarLinea(linea); linea = ""; }
    else if (linea.length() < 120) linea += c;
  }
}
