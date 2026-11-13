# BOM completo

- [BOM y CPL en Excel](../../hardware/Autonomo_V2_BOM_CPL.xlsx)
- [Pick and place (CSV)](../../hardware/Autonomo_V2_CPL.csv)

La lista tiene **52 líneas y 148 piezas**, todas montadas en la cara superior. Es la misma que se mandó a PCBWay para el ensamblaje; los números de parte son los que ellos confirmaron antes de comprar.

En pasivos, LEDs, diodos y conectores se aceptaron equivalentes. En los integrados (U1, U3, U4, U5, U21, U22, U23, U24) el sustituto tiene que ser compatible pin a pin.

**Tabla 1.** Lista de materiales de la PCB Autonomo_V2.

| # | Designadores | Cant. | Fabricante | Número de parte | Valor | Descripción | Montaje |
|---|---|---|---|---|---|---|---|
| 1 | U1 | 1 | Texas Instruments | `TPS565201DDCT` | 5 V | Buck 17 V 5 A (+5V lógica), SOT-23-6 | SMD |
| 2 | U2 | 1 | Diodes Inc. | `AP2112K-3.3TRG1` | 3.3 V | LDO 600 mA, SOT-25 | SMD |
| 3 | U3 | 1 | Espressif | `ESP32-WROOM-32E-N4` | 4 MB | Módulo ESP32, 4 MB flash | SMD |
| 4 | U4 | 1 | WCH | `CH340C` |  | Puente USB-UART, SOIC-16 | SMD |
| 5 | U5 | 1 | Toshiba | `TB6612FNG` |  | Puente H doble, SSOP-24 | SMD |
| 6 | U21, U22 | 2 | Texas Instruments | `TPS54560BDDAR` |  | Buck 60 V 5 A (+VJET 10 V y +5V_SERVO), HSOIC-8 PowerPAD | SMD |
| 7 | U23 | 1 | Texas Instruments | `SN74AHCT125DR` |  | Buffer 3.3→5 V (servo y WS2812), SOIC-14 | SMD |
| 8 | U24 | 1 | STMicroelectronics | `USBLC6-2SC6` |  | Protección ESD USB, SOT-23-6 | SMD |
| 9 | Q1, Q2, Q5 | 3 | onsemi | `MMBT3904LT1G` |  | NPN 40 V 200 mA, SOT-23 | SMD |
| 10 | Q6 | 1 | Alpha & Omega | `AO3400A` |  | MOSFET N 30 V 5.7 A, SOT-23 (luces) | SMD |
| 11 | Q7, Q8 | 2 | Alpha & Omega | `AO4407A` |  | MOSFET P 30 V 12 A, SOIC-8 (anti-inversión / corte) | SMD |
| 12 | D1, D2, D10, D11 | 4 | onsemi / genérico | `SS14` |  | Schottky 40 V 1 A, SMA | SMD |
| 13 | D3, D4 | 2 | Taiwan Semiconductor | `SK56B` |  | Schottky 60 V 5 A, SMB | SMD |
| 14 | D5, D6, D7, D8, D9 | 5 | Lite-On | `LTST-C191KGKT` | Verde | LED verde 0603 | SMD |
| 15 | D12 | 1 | Littelfuse | `SMBJ15A` | 15 V | TVS 15 V 600 W, SMB | SMD |
| 16 | D13, D14 | 2 | Diodes Inc. | `BZT52C12-7-F` | 12 V | Zener 12 V, SOD-123 (protección gate) | SMD |
| 17 | L1, L2, L3 | 3 | Würth Elektronik | `74437349047 (WE-LHMI 7050)` | 4.7 µH | Inductor de potencia blindado, 7×7 mm | SMD |
| 18 | F1 | 1 | Littelfuse | `0154010.DRL` | 10 A | Fusible SMD 10 A (portafusible OMNI-BLOK) | SMD |
| 19 | C1 | 1 | Panasonic | `EEUFR1H471` | 470 µF | Capacitor electrolítico 50 V, ±20 %, radial 12.5×20 mm, 105 °C | THT |
| 20 | C2, C4, C5, C11, C13, C15, C16, C20, C25, C33, C36, C37, C38 | 13 | Samsung Electro-Mechanics | `CL05B104KO5NNNC` | 100 nF | Capacitor cerámico 16 V, X7R, ±10 % | SMD |
| 21 | C3, C6, C7, C10, C22, C23, C28, C29, C30, C31 | 10 | Samsung Electro-Mechanics | `CL21A226MAQNNNE` | 22 µF | Capacitor cerámico 25 V, X5R, ±20 % | SMD |
| 22 | C8, C9 | 2 | Samsung Electro-Mechanics | `CL21A106KOQNNNE` | 10 µF | Capacitor cerámico 16 V, X5R, ±10 % | SMD |
| 23 | C24, C32 | 2 | Samsung Electro-Mechanics | `CL21A106KAYNNNE` | 10 µF | Capacitor cerámico 25 V, X5R (entrada de los buck, en VBAT) | SMD |
| 24 | C12 | 1 | Samsung Electro-Mechanics | `CL05A105KA5NNNC` | 1 µF | Capacitor cerámico 25 V, X5R, ±10 % | SMD |
| 25 | C14 | 1 | Panasonic | `EEUFR1H101` | 100 µF | Capacitor electrolítico 50 V, ±20 %, radial 8×11.5 mm, 105 °C | THT |
| 26 | C17, C18 | 2 | Samsung Electro-Mechanics | `CL05B102KB5NNNC` | 1 nF | Capacitor cerámico 50 V, X7R, ±10 % | SMD |
| 27 | C19 | 1 | Panasonic | `EEUFR1C471` | 470 µF | Capacitor electrolítico 16 V, ±20 %, radial 8×11.5 mm, 105 °C | THT |
| 28 | C21 | 1 | Panasonic | `EEUFR1C102` | 1000 µF | Capacitor electrolítico 16 V, ±20 %, radial 10×16 mm, 105 °C | THT |
| 29 | C26, C34 | 2 | Samsung Electro-Mechanics | `CL05B472KB5NNNC` | 4.7 nF | Capacitor cerámico 50 V, X7R, ±10 % | SMD |
| 30 | C27, C35 | 2 | Samsung Electro-Mechanics | `CL05C820JB5NNNC` | 82 pF | Capacitor cerámico 50 V, C0G, ±5 % | SMD |
| 31 | R1, R3, R36, R43 | 4 | Yageo | `RC0402FR-07100KL` | 100 kΩ | Resistencia 1 %, 1/16 W, película gruesa | SMD |
| 32 | R2, R44 | 2 | Yageo | `RC0402FR-0722KL` | 22 kΩ | Resistencia 1 %, 1/16 W, película gruesa | SMD |
| 33 | R4, R23 | 2 | Yageo | `RC0402FR-0754K9L` | 54.9 kΩ | Resistencia 1 %, 1/16 W, película gruesa | SMD |
| 34 | R5, R6, R7, R10, R11, R12, R13, R14, R15, R20, R24, R34, R37, R41, R45 | 15 | Yageo | `RC0402FR-0710KL` | 10 kΩ | Resistencia 1 %, 1/16 W, película gruesa | SMD |
| 35 | R8, R9 | 2 | Yageo | `RC0402FR-075K1L` | 5.1 kΩ | Resistencia 1 %, 1/16 W, película gruesa | SMD |
| 36 | R16 | 1 | Yageo | `RC0402FR-07220RL` | 220 Ω | Resistencia 1 %, 1/16 W, película gruesa | SMD |
| 37 | R17, R18, R27, R40 | 4 | Yageo | `RC0402FR-07330RL` | 330 Ω | Resistencia 1 %, 1/16 W, película gruesa | SMD |
| 38 | R19 | 1 | Yageo | `RC0402FR-07115KL` | 115 kΩ | Resistencia 1 %, 1/16 W, película gruesa | SMD |
| 39 | R21, R25 | 2 | Yageo | `RC0402FR-07200KL` | 200 kΩ | Resistencia 1 %, 1/16 W, película gruesa | SMD |
| 40 | R22, R26 | 2 | Yageo | `RC0402FR-078K2L` | 8.2 kΩ | Resistencia 1 %, 1/16 W, película gruesa | SMD |
| 41 | R28, R29, R30, R31, R33, R42 | 6 | Yageo | `RC0402FR-071KL` | 1 kΩ | Resistencia 1 %, 1/16 W, película gruesa | SMD |
| 42 | R32, R38, R39 | 3 | Yageo | `RC0402FR-074K7L` | 4.7 kΩ | Resistencia 1 %, 1/16 W, película gruesa | SMD |
| 43 | R35 | 1 | Yageo | `RC0402FR-07100RL` | 100 Ω | Resistencia 1 %, 1/16 W, película gruesa | SMD |
| 44 | J1 | 1 | GCT | `USB4105-GF-A` |  | Conector USB-C 2.0 receptáculo | SMD + THT (carcasa) |
| 45 | J2 | 1 | JST | `B6B-XH-AM(LF)(SN)` |  | Conector XH 6 pines vertical | THT |
| 46 | J3, J7 | 2 | JST | `B3B-XH-A(LF)(SN)` |  | Conector XH 3 pines vertical | THT |
| 47 | J4, J10, J11, J12, J14, J15 | 6 | JST | `B4B-XH-A(LF)(SN)` |  | Conector XH 4 pines vertical, paso 2.5 mm | THT |
| 48 | J5, J8, J9, P2 | 4 | Phoenix Contact | `1803277` |  | Bornera enchufable 2 pines, paso 3.81 mm | THT |
| 49 | JP1 | 1 | Würth Elektronik | `61300421121` |  | Header 2×2, paso 2.54 mm (jumper auto-reset) | THT |
| 50 | P1 | 1 | Amass | `XT60PW-M` |  | Conector XT60 macho, PCB horizontal | THT |
| 51 | S1, S2, S3 | 3 | Omron | `B3F-1000` |  | Botón táctil 6×6 mm | THT |
| 52 | TP1, TP2, TP3, TP4, TP5, TP6, TP7, TP8, TP9, TP10, TP11, TP12, TP13 | 13 | Harwin | `S1751-46R` |  | Test point SMD | SMD |

## Resumen por tipo

| Tipo | Piezas |
|---|---|
| Circuitos integrados y módulo (U) | 9 |
| Transistores y MOSFET (Q) | 6 |
| Diodos y LEDs (D) | 14 |
| Inductores (L) | 3 |
| Fusible (F) | 1 |
| Capacitores (C) | 38 |
| Resistencias (R) | 45 |
| Conectores (J) | 13 |
| Jumper (JP) | 1 |
| Conectores de potencia (P) | 2 |
| Botones (S) | 3 |
| Test points (TP) | 13 |
| **Total** | **148** |

## Notas

- C24 y C32 aparecen de 16 V en el esquemático. En el pedido van de 25 V porque están sobre VBAT (hasta 12.6 V) y con 16 V la capacitancia efectiva baja demasiado. Queda anotado para corregir el esquemático en una v3.
- Tres piezas tuvieron entrega de 7 a 10 días hábiles: los Schottky SK56B, el fusible 0154010.DRL y los test points.
- 126 piezas son SMD y 22 son through-hole (conectores, botones y electrolíticos). PCBWay suelda las dos.
