/*
 * Demo de recorrido — PCB Autonomo_V2 (RoboUAQ 2026)
 *
 * START (S3 o J10.1): arranca la secuencia.
 * BOOT  (S2):         paro inmediato en cualquier momento.
 * Paro de emergencia (J10 pines 3-4 abiertos): tambien detiene.
 *
 * Secuencia: adelante recto -> adelante girando a la izquierda ->
 *            adelante girando a la derecha -> adelante recto -> alto.
 *
 * PRIMERA VEZ: ruedas al aire. Si el motor gira hacia atras,
 * cambia DIR_ADELANTE a -1.
 */
#include <Arduino.h>
#include <ESP32Servo.h>
#include "pines_v2.h"

// ---------- Ajustes ----------
const int  DIR_ADELANTE   = 1;     // 1 o -1 segun hacia donde gire el motor
const int  VEL_CRUCERO    = 110;   // PWM 0-255. Empieza bajo
const int  VEL_ARRANQUE   = 200;   // empujon para vencer la friccion
const int  T_ARRANQUE_MS  = 150;

struct Paso { const char* nombre; int servo_us; int vel; uint32_t ms; };
const Paso SECUENCIA[] = {
  {"Adelante recto",      SERVO_CENTRO, VEL_CRUCERO, 2000},
  {"Vuelta izquierda",    SERVO_MIN,    VEL_CRUCERO, 2500},
  {"Vuelta derecha",      SERVO_MAX,    VEL_CRUCERO, 2500},
  {"Adelante recto",      SERVO_CENTRO, VEL_CRUCERO, 2000},
};
const int N_PASOS = sizeof(SECUENCIA) / sizeof(SECUENCIA[0]);

// ---------- Estado ----------
Servo servoDir;
bool corriendo = false;
int pasoActual = 0;
uint32_t tPaso = 0, tArranque = 0;

void motor(int pwm) {                  // -255..255, positivo = adelante
  pwm *= DIR_ADELANTE;
  digitalWrite(PIN_MOT_IN1, pwm > 0);
  digitalWrite(PIN_MOT_IN2, pwm < 0);
  ledcWrite(PIN_MOT_PWM, constrain(abs(pwm), 0, 255));
}

bool paroEmergencia() {                // lazo J10.3-4 abierto -> ESTOP_G ~ VBAT
  return analogReadMilliVolts(PIN_ESTOP_SENSE) / 1000.0f * VBAT_DIVISOR > 5.0f;
}

void pitido(int ms) { digitalWrite(PIN_BUZZER, HIGH); delay(ms); digitalWrite(PIN_BUZZER, LOW); }

void detener(const char* motivo) {
  motor(0);
  digitalWrite(PIN_MOT_STBY, LOW);
  servoDir.writeMicroseconds(SERVO_CENTRO);
  if (corriendo) { Serial.printf(">> ALTO (%s)\n", motivo); pitido(400); }
  corriendo = false;
}

void iniciarPaso(int i) {
  pasoActual = i;
  tPaso = millis();
  tArranque = millis();
  servoDir.writeMicroseconds(SECUENCIA[i].servo_us);
  Serial.printf("   Paso %d/%d: %s (%lu ms)\n", i + 1, N_PASOS, SECUENCIA[i].nombre, (unsigned long)SECUENCIA[i].ms);
}

void arrancar() {
  if (paroEmergencia()) { Serial.println(F(">> No arranca: paro de emergencia activo (revisa J10 pines 3-4)")); pitido(100); delay(100); pitido(100); return; }
  Serial.println(F(">> START: comienza la secuencia"));
  pitido(80); delay(80); pitido(80);
  digitalWrite(PIN_MOT_STBY, HIGH);
  corriendo = true;
  iniciarPaso(0);
}

void setup() {
  Serial.begin(115200);
  pinMode(PIN_MOT_STBY, OUTPUT); digitalWrite(PIN_MOT_STBY, LOW);
  pinMode(PIN_MOT_IN1, OUTPUT);  pinMode(PIN_MOT_IN2, OUTPUT);
  pinMode(PIN_LED_HB, OUTPUT);
  pinMode(PIN_BUZZER, OUTPUT);   digitalWrite(PIN_BUZZER, LOW);
  pinMode(PIN_START, INPUT);     // pull-up externo R37
  pinMode(0, INPUT_PULLUP);      // BOOT (S2)
  analogSetAttenuation(ADC_11db);
  ESP32PWM::allocateTimer(0);    // servo primero, luego el PWM del motor
  servoDir.setPeriodHertz(50);
  servoDir.attach(PIN_SERVO, 500, 2500);
  servoDir.writeMicroseconds(SERVO_CENTRO);
  ledcAttach(PIN_MOT_PWM, 20000, 8);
  motor(0);
  delay(300);
  Serial.println(F("\n=== Demo recorrido PCB Autonomo_V2 ==="));
  Serial.println(F("START = arrancar | BOOT = parar"));
}

void loop() {
  static bool startPrev = false;
  bool start = digitalRead(PIN_START) == LOW;
  bool boot  = digitalRead(0) == LOW;

  // Paros: siempre primero
  if (corriendo && boot)             detener("BOOT");
  if (corriendo && paroEmergencia()) detener("paro de emergencia");

  // START: flanco de bajada (solo al presionar)
  if (!corriendo && start && !startPrev) arrancar();
  startPrev = start;

  if (corriendo) {
    const Paso& p = SECUENCIA[pasoActual];
    motor(millis() - tArranque < T_ARRANQUE_MS ? VEL_ARRANQUE : p.vel);
    if (millis() - tPaso >= p.ms) {
      if (pasoActual + 1 < N_PASOS) iniciarPaso(pasoActual + 1);
      else detener("secuencia terminada");
    }
    digitalWrite(PIN_LED_HB, HIGH);                    // LED fijo = corriendo
  } else {
    digitalWrite(PIN_LED_HB, (millis() / 500) % 2);    // parpadeo = esperando
  }
  delay(5);
}
