/*
 * Prueba_PCB_Autonomo_V2 — firmware de prueba de la PCB (RoboUAQ 2026)
 * Alain Iribe Haddad
 *
 * Abre el monitor serial a 115200 y escribe el número/letra de la prueba.
 * Pines sacados del PCB de Altium (Autonomo_V2.PcbDoc).
 *
 * ANTES DE LA PRUEBA DEL MOTOR: ruedas al aire y puente entre J10 pin 3 y 4
 * (si no, el paro de emergencia deja al motor sin batería).
 */
#include <Arduino.h>
#include <Wire.h>
#include <ESP32Servo.h>
#include <Adafruit_NeoPixel.h>

// ---------- Pines (PCB Autonomo_V2) ----------
#define PIN_LED_HB      2   // LED HB (D5), HIGH = encendido
#define PIN_VBAT_SENSE 36   // divisor 100k/22k desde VBAT (solo entrada)
#define PIN_ESTOP_SENSE 39  // divisor 100k/22k desde ESTOP_G (solo entrada)
#define PIN_ENC_A      34   // encoder canal A (J2.4)
#define PIN_ENC_B      35   // encoder canal B (J2.3)
#define PIN_I2C_SDA    32   // J11/J12 pin 3
#define PIN_I2C_SCL    33   // J11/J12 pin 4
#define PIN_SERVO      25   // pasa por 74AHCT125 a 5 V -> J3
#define PIN_LED_DATA   26   // pasa por 74AHCT125 a 5 V -> J7 (WS2812)
#define PIN_START      27   // botón START (S3 y J10.1), LOW = presionado
#define PIN_LIGHTS     14   // MOSFET Q6 -> J9, HIGH = encendido
#define PIN_BUZZER     13   // transistor Q5 -> J8, HIGH = encendido
#define PIN_EXP_IO4     4   // J14 pin 2
#define PIN_EXP_IO5     5   // J14 pin 3
#define PIN_UART2_RX   16   // J4 pin 3 (RX del ESP32)
#define PIN_UART2_TX   17   // J4 pin 2 (TX del ESP32)
#define PIN_JETSON_HB  18   // J4 pin 4 (HB)
#define PIN_MOT_STBY   19   // TB6612 STBY, HIGH = habilitado
#define PIN_MOT_IN1    21   // TB6612 AIN1/BIN1 (canales en paralelo)
#define PIN_MOT_IN2    22   // TB6612 AIN2/BIN2
#define PIN_MOT_PWM    23   // TB6612 PWMA/PWMB

// ---------- Ajustes ----------
const float DIVISOR      = (100.0f + 22.0f) / 22.0f;  // R1/R2 y R43/R44
const int   MOTOR_PWM_MAX = 150;      // de 255, para la prueba
const int   SERVO_MIN = 1100, SERVO_CENTRO = 1360, SERVO_MAX = 1730;  // calibración del carro
const int   NUM_LEDS  = 8;            // LEDs de la tira que conectes en J7

Servo servoDir;
Adafruit_NeoPixel tira(NUM_LEDS, PIN_LED_DATA, NEO_GRB + NEO_KHZ800);
volatile int32_t encoderCount = 0;

void IRAM_ATTR encoderISR() {
  if (digitalRead(PIN_ENC_A)) {
    if (digitalRead(PIN_ENC_B)) encoderCount -= 1;
    else                        encoderCount += 1;
  }
}

float leerVolt(int pin) {               // voltaje real antes del divisor
  uint32_t mv = 0;
  for (int i = 0; i < 16; i++) mv += analogReadMilliVolts(pin);
  return (mv / 16.0f) / 1000.0f * DIVISOR;
}
bool paroActivo() { return leerVolt(PIN_ESTOP_SENSE) > 5.0f; }  // lazo J10.3-4 abierto -> ESTOP_G ≈ VBAT

void motor(int pwm) {                   // -255..255
  digitalWrite(PIN_MOT_IN1, pwm > 0);
  digitalWrite(PIN_MOT_IN2, pwm < 0);
  ledcWrite(PIN_MOT_PWM, abs(pwm));
}

bool esperar(uint32_t ms) {             // espera; regresa true si escribiste algo para cancelar
  uint32_t t0 = millis();
  while (millis() - t0 < ms) { if (Serial.available()) { while (Serial.available()) Serial.read(); return true; } delay(5); }
  return false;
}

void menu() {
  Serial.println();
  Serial.println(F("===== PRUEBA PCB Autonomo_V2 ====="));
  Serial.println(F(" 1  LED HB (parpadeo)"));
  Serial.println(F(" 2  Voltajes: bateria y paro de emergencia"));
  Serial.println(F(" 3  Boton START y paro (10 s)"));
  Serial.println(F(" 4  Motor + encoder (ruedas al aire!)"));
  Serial.println(F(" 5  Encoder a mano (15 s)"));
  Serial.println(F(" 6  Servo (barrido)"));
  Serial.println(F(" 7  Buzzer"));
  Serial.println(F(" 8  Luces (J9)"));
  Serial.println(F(" 9  Tira LED (J7)"));
  Serial.println(F(" a  UART Jetson (J4) 15 s"));
  Serial.println(F(" b  Escaneo I2C (J11/J12)"));
  Serial.println(F(" c  GPIO extra IO4/IO5 (J14)"));
  Serial.println(F(" d  Linea HB de J4 (lectura)"));
  Serial.println(F(" Escribe la opcion. Cualquier tecla cancela una prueba."));
}

void pruebaLed() {
  Serial.println(F("[1] LED HB parpadea 10 veces"));
  for (int i = 0; i < 10; i++) { digitalWrite(PIN_LED_HB, HIGH); if (esperar(200)) break; digitalWrite(PIN_LED_HB, LOW); if (esperar(200)) break; }
  digitalWrite(PIN_LED_HB, LOW);
  Serial.println(F("    ¿Parpadeo el LED HB? Si no: revisa D5/R28."));
}

void pruebaVoltajes() {
  Serial.println(F("[2] Compara con el multimetro (5 lecturas)"));
  for (int i = 0; i < 5; i++) {
    float vb = leerVolt(PIN_VBAT_SENSE), ve = leerVolt(PIN_ESTOP_SENSE);
    Serial.printf("    VBAT = %.2f V | ESTOP_G = %.2f V -> %s\n", vb, ve, ve > 5.0f ? "PARO ACTIVO (lazo J10 abierto)" : "OK (lazo J10 cerrado)");
    if (esperar(1000)) break;
  }
  Serial.println(F("    Si VBAT difiere del multimetro, ajusta DIVISOR (calibracion)."));
}

void pruebaBotones() {
  Serial.println(F("[3] Presiona START (S3 o el de J10) y abre/cierra el paro. 10 s"));
  int s0 = -1, e0 = -1; uint32_t t0 = millis();
  while (millis() - t0 < 10000) {
    int s = digitalRead(PIN_START) == LOW, e = paroActivo();
    if (s != s0) { Serial.println(s ? F("    START presionado") : F("    START suelto")); s0 = s; }
    if (e != e0) { Serial.println(e ? F("    PARO ACTIVO") : F("    Paro liberado")); e0 = e; }
    if (Serial.available()) { while (Serial.available()) Serial.read(); break; }
    delay(30);
  }
}

void pruebaMotor() {
  Serial.println(F("[4] Motor: rampa adelante, luego atras. RUEDAS AL AIRE."));
  if (paroActivo()) { Serial.println(F("    Paro activo: pon el puente J10.3-4 y repite.")); return; }
  digitalWrite(PIN_MOT_STBY, HIGH);
  for (int dir = 1; dir >= -1; dir -= 2) {
    Serial.println(dir > 0 ? F("    -> Adelante") : F("    -> Atras"));
    encoderCount = 0;
    for (int p = 0; p <= MOTOR_PWM_MAX; p += 10) {
      motor(dir * p);
      if (esperar(150)) { motor(0); digitalWrite(PIN_MOT_STBY, LOW); return; }
      Serial.printf("      PWM %3d  encoder %ld\n", dir * p, (long)encoderCount);
      if (paroActivo()) { motor(0); Serial.println(F("    Paro activado: el motor debe detenerse aunque haya PWM. OK")); digitalWrite(PIN_MOT_STBY, LOW); return; }
    }
    for (int p = MOTOR_PWM_MAX; p >= 0; p -= 15) { motor(dir * p); delay(80); }
    motor(0);
    Serial.printf("    Pulsos totales: %ld (adelante debe ser +, atras -; si no, invierte en el firmware del carro)\n", (long)encoderCount);
    if (esperar(800)) break;
  }
  motor(0); digitalWrite(PIN_MOT_STBY, LOW);
  Serial.println(F("    Tip: con el motor girando, quita el puente de J10: debe pararse solo."));
}

void pruebaEncoder() {
  Serial.println(F("[5] Gira la rueda a mano. 15 s"));
  encoderCount = 0; long last = 0; uint32_t t0 = millis();
  while (millis() - t0 < 15000) {
    long c = encoderCount;
    if (c != last) { Serial.printf("    pulsos: %ld  (%.2f vueltas)\n", c, c / 360.0f); last = c; }
    if (esperar(100)) break;
  }
}

void pruebaServo() {
  Serial.println(F("[6] Servo: centro, izquierda, derecha, centro"));
  int pos[] = {SERVO_CENTRO, SERVO_MIN, SERVO_CENTRO, SERVO_MAX, SERVO_CENTRO};
  for (int p : pos) { Serial.printf("    %d us\n", p); servoDir.writeMicroseconds(p); if (esperar(800)) break; }
  servoDir.writeMicroseconds(SERVO_CENTRO);
}

void pruebaBuzzer() {
  Serial.println(F("[7] Buzzer: 3 pitidos"));
  for (int i = 0; i < 3; i++) { digitalWrite(PIN_BUZZER, HIGH); if (esperar(200)) break; digitalWrite(PIN_BUZZER, LOW); if (esperar(200)) break; }
  digitalWrite(PIN_BUZZER, LOW);
  Serial.println(F("    Si no suena y es buzzer pasivo, necesitas tone(); si es activo, revisa Q5/R33."));
}

void pruebaLuces() {
  Serial.println(F("[8] Luces J9 (VBAT): 3 encendidos de 1 s"));
  for (int i = 0; i < 3; i++) { digitalWrite(PIN_LIGHTS, HIGH); if (esperar(1000)) break; digitalWrite(PIN_LIGHTS, LOW); if (esperar(500)) break; }
  digitalWrite(PIN_LIGHTS, LOW);
}

void pruebaTira() {
  Serial.printf("[9] Tira LED (%d LEDs): rojo, verde, azul, blanco\n", NUM_LEDS);
  uint32_t col[] = {tira.Color(60,0,0), tira.Color(0,60,0), tira.Color(0,0,60), tira.Color(40,40,40)};
  for (uint32_t c : col) { tira.fill(c); tira.show(); if (esperar(700)) break; }
  tira.clear(); tira.show();
}

void pruebaUart() {
  Serial.println(F("[a] UART2 a 115200 por J4 (pin2 = TX, pin3 = RX). 15 s"));
  Serial.println(F("    Sin Jetson: puentea J4 pin 2 con pin 3 y debe regresar lo mismo."));
  Serial2.begin(115200, SERIAL_8N1, PIN_UART2_RX, PIN_UART2_TX);
  uint32_t t0 = millis(), tx = 0; int n = 0;
  while (millis() - t0 < 15000) {
    if (millis() - tx > 1000) { tx = millis(); Serial2.printf("PING %d\n", n); Serial.printf("    -> PING %d\n", n++); }
    while (Serial2.available()) { String l = Serial2.readStringUntil('\n'); Serial.print(F("    <- ")); Serial.println(l); }
    if (Serial.available()) { while (Serial.available()) Serial.read(); break; }
    delay(5);
  }
  Serial2.end();
}

void pruebaI2C() {
  Serial.println(F("[b] Escaneo I2C (SDA 32, SCL 33)"));
  int n = 0;
  for (uint8_t a = 1; a < 127; a++) { Wire.beginTransmission(a); if (Wire.endTransmission() == 0) { Serial.printf("    Dispositivo en 0x%02X\n", a); n++; } }
  Serial.printf("    %d dispositivo(s)\n", n);
}

void pruebaGpio() {
  Serial.println(F("[c] J14: IO4 e IO5 alternan cada 500 ms (mide con multimetro o LED+resistencia)"));
  pinMode(PIN_EXP_IO4, OUTPUT); pinMode(PIN_EXP_IO5, OUTPUT);
  for (int i = 0; i < 10; i++) { digitalWrite(PIN_EXP_IO4, i % 2); digitalWrite(PIN_EXP_IO5, !(i % 2)); if (esperar(500)) break; }
  digitalWrite(PIN_EXP_IO4, LOW); digitalWrite(PIN_EXP_IO5, LOW);
}

void pruebaHB() {
  Serial.println(F("[d] Lectura de J4 pin 4 (HB) por 10 s"));
  pinMode(PIN_JETSON_HB, INPUT_PULLDOWN);
  int last = -1; uint32_t t0 = millis();
  while (millis() - t0 < 10000) { int v = digitalRead(PIN_JETSON_HB); if (v != last) { Serial.printf("    HB = %d\n", v); last = v; } if (esperar(20)) break; }
}

void setup() {
  Serial.begin(115200);
  delay(300);
  pinMode(PIN_LED_HB, OUTPUT);   digitalWrite(PIN_LED_HB, LOW);
  pinMode(PIN_BUZZER, OUTPUT);   digitalWrite(PIN_BUZZER, LOW);
  pinMode(PIN_LIGHTS, OUTPUT);   digitalWrite(PIN_LIGHTS, LOW);
  pinMode(PIN_MOT_STBY, OUTPUT); digitalWrite(PIN_MOT_STBY, LOW);
  pinMode(PIN_MOT_IN1, OUTPUT);  pinMode(PIN_MOT_IN2, OUTPUT);
  pinMode(PIN_START, INPUT);     // pull-up externo R37
  pinMode(PIN_ENC_A, INPUT);     pinMode(PIN_ENC_B, INPUT);  // GPIO34/35 sin pull interno; la placa trae R14/R15
  analogSetAttenuation(ADC_11db);
  ESP32PWM::allocateTimer(0);    // servo primero, luego el PWM del motor
  servoDir.setPeriodHertz(50);
  servoDir.attach(PIN_SERVO, 500, 2500);
  servoDir.writeMicroseconds(SERVO_CENTRO);
  ledcAttach(PIN_MOT_PWM, 20000, 8);
  motor(0);
  attachInterrupt(digitalPinToInterrupt(PIN_ENC_A), encoderISR, CHANGE);
  Wire.begin(PIN_I2C_SDA, PIN_I2C_SCL);
  tira.begin(); tira.clear(); tira.show();
  menu();
}

void loop() {
  static uint32_t hb = 0;
  if (millis() - hb > 1000) { hb = millis(); digitalWrite(PIN_LED_HB, !digitalRead(PIN_LED_HB)); }  // latido normal
  if (!Serial.available()) return;
  char c = Serial.read();
  while (Serial.available()) Serial.read();
  switch (c) {
    case '1': pruebaLed(); break;      case '2': pruebaVoltajes(); break;
    case '3': pruebaBotones(); break;  case '4': pruebaMotor(); break;
    case '5': pruebaEncoder(); break;  case '6': pruebaServo(); break;
    case '7': pruebaBuzzer(); break;   case '8': pruebaLuces(); break;
    case '9': pruebaTira(); break;     case 'a': pruebaUart(); break;
    case 'b': pruebaI2C(); break;      case 'c': pruebaGpio(); break;
    case 'd': pruebaHB(); break;
    default: break;
  }
  menu();
}
