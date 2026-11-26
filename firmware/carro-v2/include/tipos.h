// Estructuras del carro. Cada modulo trabaja con apuntadores a estas.
#pragma once
#include <Arduino.h>
#include <ESP32Servo.h>
#include "config.h"

// Motor de traccion (TB6612)
typedef struct {
  uint8_t pin_pwm, pin_in1, pin_in2, pin_stby;
  int pwm_actual;       // -255..255, lo que esta saliendo ahora
  int pwm_objetivo;     // -255..255, a donde va la rampa
  uint32_t t_rampa_ms;  // ultimo paso de rampa
} Motor;

// Direccion (servo). us_* siempre dentro de SERVO_MIN..SERVO_MAX
typedef struct {
  uint8_t pin;
  Servo servo;
  float us_actual;      // posicion que mandamos (se mueve suave)
  int us_objetivo;
  int us_escrito;       // ultimo valor enviado al servo
  uint32_t t_ultimo_ms;
} Direccion;

// Encoder de cuadratura. La ISR modifica 'cuenta'
typedef struct {
  uint8_t pin_a, pin_b;
  volatile int32_t cuenta;
  int32_t cuenta_previa;
  uint32_t t_previo_ms;
  int pulsos_s;         // velocidad medida, con signo
} Encoder;

// Ultimo comando recibido de la Jetson
typedef struct {
  int vel;              // -100..100 (%)
  int dir;              // -100..100 (-100 izquierda, 100 derecha)
  uint32_t t_ultimo_ms; // cuando llego el ultimo V/S valido
  bool recibido;        // ya llego al menos uno
  Stream *puerto;       // por donde contestar
} Comando;

// Buffer de recepcion de un puerto (tamano fijo, sin String)
typedef struct {
  Stream *puerto;
  char buf[LINEA_MAX];
  uint8_t n;
  bool desbordado;      // la linea no cupo: se descarta hasta el \n
} LineaRx;

// Boton con antirrebote
typedef struct {
  uint8_t pin;
  bool pulsado;         // estado estable
  bool lectura_previa;
  uint32_t t_cambio_ms;
} Boton;

// Bateria (VBAT por ADC, promedio movil)
typedef struct {
  uint16_t muestras[BAT_N_MUESTRAS];
  uint8_t idx;
  uint32_t suma;
  int mv;               // voltaje de bateria promediado, en mV
  bool presente;        // false = solo USB
  bool baja;            // < 10.5 V sostenido
  bool critica;         // < 9.9 V sostenido
  bool cont_baja, cont_critica;       // se esta contando el tiempo
  uint32_t t_baja_ms, t_critica_ms;   // desde cuando
  uint32_t t_muestra_ms;
  bool inicializada;
} Bateria;

// Paro de emergencia: lazo J10 (ADC) y BOOT/START (software)
typedef struct {
  bool hw;              // lazo J10 abierto
  bool sw;              // BOOT presionado (se libera con START)
  uint8_t cuenta_on, cuenta_off;
  int mv_estop;         // ultimo voltaje calculado en ESTOP_G, mV
  uint32_t t_muestra_ms;
  Boton boot, start;
} Paro;

// Todo el carro junto
typedef struct {
  Motor motor;
  Direccion dir;
  Encoder enc;
  Comando cmd;
  Bateria bat;
  Paro paro;
  LineaRx rx_usb, rx_uart2;
  uint8_t estado;       // ESTADO_*
  bool timeout;
  uint32_t t_telem_ms;
  uint32_t t_led_ms;
  bool led;
  uint32_t t_buzzer_ms;
  bool buzzer;
} Carro;
