# Programar el ESP32

El firmware se carga por el USB-C de la placa. No hace falta programador externo ni conectar la batería.

## Preparación

1. Instala [Visual Studio Code](https://code.visualstudio.com/) y la extensión [PlatformIO](https://platformio.org/).
2. Conecta la placa con un cable USB-C de datos. Enciende el LED 3V3.
3. La computadora debe mostrar un puerto serial nuevo (CH340). Si no aparece, instala el driver del CH340 del fabricante, WCH.

## Configuración del proyecto

El módulo es un ESP32-WROOM-32E, compatible con la definición de tarjeta del DevKit:

```ini
[env:esp32doit-devkit-v1]
platform = espressif32
board = esp32doit-devkit-v1
framework = arduino
monitor_speed = 115200
upload_speed = 921600
```

## Cargar

1. Verifica que los dos puentes de **JP1** estén puestos.
2. En PlatformIO, da clic en **Upload**. El auto-reset pone al ESP32 en modo de carga y lo reinicia al terminar.
3. Abre el monitor serial a 115200 baudios.

### Carga manual

Si el auto-reset está deshabilitado o falla:

1. Mantén presionado **BOOT** (S2).
2. Presiona y suelta **EN** (S1).
3. Suelta BOOT e inicia la carga.
4. Al terminar, presiona EN para arrancar el programa.

## Con un programador externo

El conector J15 expone TX0, RX0, GND y 3.3 V. Sirve para usar un adaptador USB-serial propio si el CH340C de la placa fallara. Hay que cruzar las líneas (TX del adaptador a RX0) y entrar al modo de carga con los botones.

## Pines que no se deben mover

Al escribir firmware nuevo, toma los pines de la [tabla de GPIO](../hardware/pinout.md). Tres detalles que suelen causar problemas:

- IO34, IO35, IO36 e IO39 son solo entradas y no tienen pull-up interno.
- IO0 e IO2 afectan el arranque. IO2 tiene el LED HB, que no estorba.
- Con la librería ESP32Servo hay que reservar el timer del servo **antes** de configurar el PWM del motor:

```cpp
ESP32PWM::allocateTimer(0);        // primero el servo
servo.setPeriodHertz(50);
servo.attach(25, 500, 2500);
ledcAttach(23, 20000, 8);          // después el PWM del motor, 20 kHz
```
