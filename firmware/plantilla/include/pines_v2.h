// Pines de la PCB Autonomo_V2 (sacados del PcbDoc de Altium).
// Incluyelo con:  #include "pines_v2.h"
#pragma once

#define PIN_LED_HB       2   // LED HB (D5), HIGH = encendido
#define PIN_VBAT_SENSE  36   // divisor 100k/22k desde VBAT. V = lectura * 5.545
#define PIN_ESTOP_SENSE 39   // divisor 100k/22k desde ESTOP_G. Leer con ADC
#define PIN_ENC_A       34   // encoder canal A (J2.4)
#define PIN_ENC_B       35   // encoder canal B (J2.3)
#define PIN_I2C_SDA     32   // J11/J12 pin 3 -> Wire.begin(32, 33)
#define PIN_I2C_SCL     33   // J11/J12 pin 4
#define PIN_SERVO       25   // buffer a 5 V -> J3
#define PIN_LED_DATA    26   // buffer a 5 V -> J7 (WS2812)
#define PIN_START       27   // boton START (S3 y J10.1), LOW = presionado
#define PIN_LIGHTS      14   // MOSFET Q6 -> J9, HIGH = encendido
#define PIN_BUZZER      13   // transistor Q5 -> J8, HIGH = encendido
#define PIN_EXP_IO4      4   // J14 pin 2 (ADC2: no lee analogico con WiFi)
#define PIN_EXP_IO5      5   // J14 pin 3 (strapping: debe estar alto al arrancar)
#define PIN_UART2_RX    16   // J4 pin 3 (RX del ESP32)
#define PIN_UART2_TX    17   // J4 pin 2 (TX del ESP32)
#define PIN_JETSON_HB   18   // J4 pin 4 (HB)
#define PIN_MOT_STBY    19   // TB6612 STBY, HIGH = habilitado
#define PIN_MOT_IN1     21   // TB6612 AIN1/BIN1
#define PIN_MOT_IN2     22   // TB6612 AIN2/BIN2
#define PIN_MOT_PWM     23   // TB6612 PWMA/PWMB

const float VBAT_DIVISOR = (100.0f + 22.0f) / 22.0f;
const int SERVO_MIN = 1100, SERVO_CENTRO = 1360, SERVO_MAX = 1730;  // calibracion del carro
