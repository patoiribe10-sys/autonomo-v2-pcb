# Pinout

Las tablas salen del archivo de la PCB, no del plan original. Son las que hay que usar al escribir firmware o armar cables.

## Pines del ESP32

Los pines que ya usaba el carro (motor, encoder, servo y UART) se conservaron para no tocar el firmware. Lo demás es nuevo en esta versión.

**Tabla 1.** Asignación de GPIO.

| GPIO | Señal | Va a | Notas |
|---|---|---|---|
| 0 | BOOT | S2 y auto-reset | Modo de carga |
| 1 / 3 | TX0 / RX0 | CH340C y J15 | Programación y monitor serial |
| 2 | LED_HB | LED D5 | Alto = encendido |
| 4 | EXP_IO4 | J14 pin 2 | Libre |
| 5 | EXP_IO5 | J14 pin 3 | Libre |
| 13 | BUZZER | Q5 → J8 | Alto = suena |
| 14 | LIGHTS | Q6 → J9 | Alto = luces encendidas |
| 16 | UART2_RX | J4 pin 3 | Recibe de la Jetson. 330 Ω en serie |
| 17 | UART2_TX | J4 pin 2 | Envía a la Jetson. 330 Ω en serie |
| 18 | JETSON_HB | J4 pin 4 | Línea de heartbeat. 330 Ω en serie |
| 19 | MOT_STBY | TB6612 STBY | Alto = puente H habilitado. Pull-up de 10 kΩ |
| 21 | MOT_IN1 | TB6612 AIN1 y BIN1 | Sentido de giro |
| 22 | MOT_IN2 | TB6612 AIN2 y BIN2 | Sentido de giro |
| 23 | MOT_PWM | TB6612 PWMA y PWMB | Velocidad |
| 25 | SERVO_3V3 | U23 → J3 | Señal del servo, sale a 5 V |
| 26 | LED_DATA_3V3 | U23 → J7 | Datos WS2812, salen a 5 V |
| 27 | START_BTN | S3 y J10 pin 1 | Bajo = presionado. Pull-up de 10 kΩ |
| 32 | I2C_SDA | J11 y J12 pin 3 | Pull-up de 4.7 kΩ |
| 33 | I2C_SCL | J11 y J12 pin 4 | Pull-up de 4.7 kΩ |
| 34 | ENC_A | J2 pin 4 | Solo entrada. Pull-up externo de 10 kΩ |
| 35 | ENC_B | J2 pin 3 | Solo entrada. Pull-up externo de 10 kΩ |
| 36 | VBAT_SENSE | Divisor desde VBAT | Solo entrada. V = lectura × 5.545 |
| 39 | ESTOP_SENSE | Divisor desde la compuerta de Q8 | Solo entrada. Cerca de VBAT con el paro activo, cerca de 0 V con el lazo cerrado |
| EN | Reset | S1 y auto-reset | |

> ESTOP_SENSE se lee con el convertidor analógico, no con `digitalRead`. Con una batería baja el nivel alto queda muy cerca del umbral digital.

## Conectores

El pin 1 de cada conector está marcado en la serigrafía. La función de cada pin también está impresa junto al conector.

### J2 · MOTOR + ENCODER (XH de 6 pines)

| Pin | Señal |
|---|---|
| 1 | MOT_B (motor −) |
| 2 | 3.3 V (alimentación del encoder) |
| 3 | ENC_B |
| 4 | ENC_A |
| 5 | GND |
| 6 | MOT_A (motor +) |

### J3 · SERVO 5V (XH de 3 pines)

| Pin | Señal |
|---|---|
| 1 | GND |
| 2 | 5 V del servo |
| 3 | PWM a 5 V |

### J4 · SERIAL JETSON (XH de 4 pines)

| Pin | Señal | Pin del header de 40 de la Jetson |
|---|---|---|
| 1 | GND | 6 |
| 2 | TX del ESP32 | 10 (RXD) |
| 3 | RX del ESP32 | 8 (TXD) |
| 4 | HB | Sin conectar por ahora |

### J5 · ALIM. JETSON 10V (Phoenix de 2 pines)

| Pin | Señal |
|---|---|
| 1 | +10 V |
| 2 | GND |

### J7 · TIRA LED RGB (XH de 3 pines)

| Pin | Señal |
|---|---|
| 1 | GND |
| 2 | 5 V |
| 3 | DIN |

### J8 · BUZZER y J9 · LUCES (Phoenix de 2 pines)

| Conector | Pin 1 | Pin 2 |
|---|---|---|
| J8 | +5 V | Retorno conmutado por Q5 |
| J9 | VBAT | Retorno conmutado por Q6 |

En los dos la carga se conecta entre el positivo y el retorno. El transistor cierra el circuito hacia GND, y cada salida tiene su diodo de protección para cargas inductivas.

### J10 · START / PARO EMERG. (XH de 4 pines)

| Pin | Señal |
|---|---|
| 1 | START (botón a GND) |
| 2 | GND |
| 3 | ESTOP (lazo del paro) |
| 4 | GND |

El botón de paro, normalmente cerrado, va entre los pines 3 y 4.

### J11 y J12 · SENSORES I2C (XH de 4 pines)

| Pin | Señal |
|---|---|
| 1 | GND |
| 2 | 3.3 V |
| 3 | SDA |
| 4 | SCL |

### J14 · GPIO EXTRA (XH de 4 pines)

| Pin | Señal |
|---|---|
| 1 | 3.3 V |
| 2 | IO4 |
| 3 | IO5 |
| 4 | GND |

### J15 · SERIAL/PROG ESP32 (XH de 4 pines)

| Pin | Señal |
|---|---|
| 1 | TX0 del ESP32 |
| 2 | RX0 del ESP32 |
| 3 | GND |
| 4 | 3.3 V |

TX y RX están nombrados desde el ESP32. Con un adaptador externo se cruzan: TX con RX.

### P1 · BATERIA y P2 · SWITCH

| Conector | Pines |
|---|---|
| P1 (XT60) | + y −, marcados en la serigrafía |
| P2 (Phoenix) | IN y OUT del interruptor |

### JP1 · AUTO-RESET (header 2×2)

Un puente une la línea EN del auto-reset con el EN del ESP32 y el otro hace lo mismo con IO0.

## Puentes para pruebas en banco

Para encender la placa sin el carro hacen falta dos:

- Un puente en **P2**, que hace de interruptor.
- Un puente entre los **pines 3 y 4 de J10**. Sin él, el paro de emergencia deja al motor sin batería.
