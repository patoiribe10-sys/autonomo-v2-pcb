# Conectividad: USB y Bluetooth

La placa tiene cuatro formas de comunicarse: USB con la computadora, UART con la Jetson, y Bluetooth y Wi-Fi por la antena del ESP32.

| Enlace | Hardware | Para qué |
|---|---|---|
| USB | J1, U24, U4 | Programar y ver el monitor serial |
| UART con la Jetson | J4 | Órdenes de velocidad y dirección, telemetría |
| UART de servicio | J15 | Programador externo o depuración |
| Bluetooth | Módulo U3 | Telemetría y ajustes sin cable |
| Wi-Fi | Módulo U3 | Disponible, sin uso por ahora |
| I2C | J11, J12 | Sensores |

## USB

El conector es un USB-C trabajando como dispositivo USB 2.0. No carga la batería ni alimenta el carro: sirve para datos y para dar energía al ESP32 mientras se programa.

| Elemento | Función |
|---|---|
| J1 (USB4105-GF-A) | Receptáculo USB-C |
| R8, R9 (5.1 kΩ a GND en CC1 y CC2) | Le indican a la computadora o al cargador que hay un dispositivo y que debe entregar 5 V. Sin ellas, un cable C a C no enciende la placa |
| U24 (USBLC6-2SC6) | Protección contra descargas electrostáticas en D+ y D− |
| U4 (CH340C) | Convierte USB a UART. Aparece en la computadora como un puerto serial |
| Q1, Q2, JP1 | Auto-reset con DTR y RTS |
| D2 | Lleva el VBUS al regulador de 3.3 V |

D+ y D− se rutearon juntas y cortas, con una regla de ancho propia (clase USB).

**Configuración del puerto:** 115200 baudios para el monitor serial; la carga del firmware usa 921600.

### Cuándo quitar los puentes de JP1

Con los puentes puestos, abrir el puerto desde la computadora reinicia al ESP32, que es lo que se quiere al programar. Si en algún momento la Jetson se conecta por USB en lugar de por J4, conviene quitarlos para que el micro no se reinicie cada vez que arranca el programa.

## UART con la Jetson

| Parámetro | Valor |
|---|---|
| Puerto del ESP32 | UART2 (RX en IO16, TX en IO17) |
| Velocidad | 115200 baudios, 8N1 |
| Nivel | 3.3 V en los dos lados, sin convertidor |
| Protección | 330 Ω en serie en TX, RX y HB |
| Puntos de prueba | TP5 (TX) y TP6 (RX) |

El cable es un XH de 4 pines a terminales dupont hembra:

| J4 | Señal | Header de la Jetson |
|---|---|---|
| 1 | GND | Pin 6 |
| 2 | TX del ESP32 | Pin 10 (RXD) |
| 3 | RX del ESP32 | Pin 8 (TXD) |
| 4 | HB | Sin conectar |

En la v1 este enlace no funcionó por hardware y se terminó usando USB. Por eso ahora tiene resistencias en serie y un test point en cada línea: es de lo primero que se va a medir cuando llegue la placa.

## Bluetooth

El ESP32-WROOM-32E trae el radio integrado, con antena en el mismo módulo. No hay ningún componente adicional en la placa para Bluetooth; lo que sí se cuidó fue el lugar del módulo.

| Característica | Valor |
|---|---|
| Estándar | Bluetooth 4.2, clásico (BR/EDR) y de bajo consumo (BLE) |
| Banda | 2.4 GHz, compartida con el Wi-Fi |
| Antena | De pista, en el propio módulo |

**En el diseño de la PCB:**

- El módulo está en el borde superior, con la antena hacia afuera.
- Debajo de la antena no hay cobre en ninguna de las cuatro capas.
- Los reguladores conmutados quedaron en el lado opuesto de la placa.

**Para qué se piensa usar:** ver desde un teléfono la velocidad, el voltaje de batería y el estado del paro mientras el carro corre. También para ajustar parámetros, como las ganancias del control, sin conectar un cable. Con Bluetooth clásico el ESP32 se presenta como un puerto serial, así que basta una aplicación de terminal.

Un ejemplo mínimo con el framework Arduino:

```cpp
#include <BluetoothSerial.h>
BluetoothSerial BT;

void setup() {
  BT.begin("Autonomo_V2");          // nombre con el que aparece al emparejar
}

void loop() {
  BT.printf("VBAT %.2f V\n", analogReadMilliVolts(36) / 1000.0 * 5.545);
  delay(1000);
}
```

> El firmware actual del carro todavía no usa Bluetooth, y este ejemplo no se ha probado en la placa porque sigue en fabricación. Queda como siguiente paso después de las pruebas eléctricas.

## Wi-Fi

Mismo radio y misma antena: 802.11 b/g/n en 2.4 GHz. No tiene uso asignado. La opción más útil a futuro sería cargar firmware por red (OTA) sin sacar el carro de la pista.

## I2C

Dos conectores iguales, J11 y J12, sobre el mismo bus (SDA en IO32, SCL en IO33) con pull-up de 4.7 kΩ a 3.3 V. Los sensores que se conecten deben trabajar a 3.3 V.
