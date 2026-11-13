# Componentes principales

De las 148 piezas, estas son las que definen lo que la placa puede hacer. La lista completa está en el [BOM](bom.md).

**Tabla 1.** Componentes principales.

| Ref. | Número de parte | Fabricante | Función |
|---|---|---|---|
| U3 | ESP32-WROOM-32E-N4 | Espressif | Microcontrolador con Wi-Fi y Bluetooth, 4 MB de flash |
| U5 | TB6612FNG | Toshiba | Puente H del motor |
| U1 | TPS565201DDCT | Texas Instruments | Regulador conmutado de 5 V para la lógica |
| U21 | TPS54560BDDAR | Texas Instruments | Regulador conmutado de 10 V para la Jetson |
| U22 | TPS54560BDDAR | Texas Instruments | Regulador conmutado de 5 V para el servo |
| U2 | AP2112K-3.3TRG1 | Diodes Inc. | Regulador lineal de 3.3 V, 600 mA |
| U4 | CH340C | WCH | Convertidor USB a serial |
| U23 | SN74AHCT125DR | Texas Instruments | Buffer que sube señales de 3.3 V a 5 V |
| U24 | USBLC6-2SC6 | STMicroelectronics | Protección ESD de las líneas USB |
| Q7, Q8 | AO4407A | Alpha & Omega | MOSFET canal P: anti-inversión y corte del motor |
| Q6 | AO3400A | Alpha & Omega | MOSFET canal N que enciende las luces |
| D12 | SMBJ15A | Littelfuse | Supresor de picos en la entrada de batería |
| F1 | 0154010.DRL | Littelfuse | Fusible de 10 A con portafusible SMD |
| L1, L2, L3 | 74437349047 | Würth Elektronik | Inductores de 4.7 µH de los tres reguladores |
| D3, D4 | SK56B | Taiwan Semiconductor | Diodos Schottky de 5 A de U21 y U22 |

## Por qué estos

### ESP32-WROOM-32E

Es el mismo micro que usaba la v1 en forma de DevKit, así que el firmware del carro corre sin cambios. Aquí va el módulo soldado directo: ocupa menos, no depende de headers y trae la antena y el blindaje certificados. La versión N4 tiene 4 MB de flash, de sobra para el firmware actual.

### TB6612FNG con los canales en paralelo

El motor es un GM25-370 con encoder. El TB6612 entrega 1.2 A continuos por canal; uniendo A y B en paralelo el margen se duplica y un solo juego de señales (IN1, IN2, PWM) maneja los dos. El pin STBY lleva pull-up a 3.3 V, que era justo lo que fallaba en la placa anterior.

### Dos TPS54560B y un TPS565201

La Jetson pide hasta 25 W y el servo MG995 tiene picos de 2.5 a 3 A. Los dos se alimentan con un TPS54560B, que aguanta 5 A y hasta 60 V de entrada. Se usa la versión "B" porque la que no tiene esa letra ya aparece como no recomendada para diseños nuevos. No es síncrono, por eso cada uno lleva su diodo Schottky (D3 y D4).

La lógica consume menos de medio ampere, así que para ella basta el TPS565201, que es síncrono y no necesita diodo externo.

Tener el servo en un regulador aparte fue una decisión directa de la experiencia con la v1: cada golpe de dirección tiraba los 5 V y reiniciaba el ESP32.

### CH340C

Convierte USB a serial y no necesita cristal externo. Es el mismo chip del DevKit, de modo que los drivers ya estaban instalados en las computadoras del equipo.

### SN74AHCT125

El ESP32 saca 3.3 V y tanto el servo como la tira WS2812 esperan señales de 5 V. Este buffer se alimenta a 5 V y reconoce 3.3 V como nivel alto, así que hace la conversión sin más piezas.

### AO4407A

Se usa dos veces. En Q7 protege contra una batería conectada al revés, con mucha menos caída de voltaje que un diodo. En Q8 es el interruptor que el paro de emergencia abre para quitarle la batería al motor. Cada uno tiene un zener de 12 V (D13, D14) que cuida la compuerta.

## Criterios generales

- **Montaje superficial siempre que se pueda.** PCBWay ensambla la placa, y lo SMD sale más barato y repetible. Solo son through-hole los conectores, los botones y los capacitores electrolíticos.
- **Nada de encapsulados sin patas.** No hay QFN ni BGA, para que el acabado HASL sea suficiente y se pueda retrabajar con cautín.
- **Pasivos 0402 y 0805** de Yageo y Samsung, que casi cualquier ensamblador tiene en existencia.
- **Sustitutos.** En pasivos y conectores se aceptan equivalentes. En integrados, solo compatibles pin a pin.
