# Firmware de la PCB Autonomo_V2

Todo lo que se carga al ESP32 de la placa va en esta carpeta. Cada programa es un proyecto de PlatformIO.

| Carpeta | Para qué |
|---|---|
| `carro-v2/` | **Firmware definitivo del carro.** Recibe `V<vel>,S<dir>` de la Jetson y manda telemetría a 20 Hz, con paro de emergencia, timeout y vigilancia de batería. Tiene su propio `README.md`. |
| `prueba-pcb/` | Firmware de prueba con menú por serial (115200) de 13 pruebas: voltajes, motor y encoder, servo, buzzer, luces, tira LED, UART2, I2C. Úsalo cada vez que conectes algo nuevo. |
| `prueba-usb/` | Prueba mínima solo con el cable USB-C: latido con voltaje de batería, eco, botones START y BOOT y LED HB. |
| `demo-recorrido/` | Recorrido corto sin Jetson: START arranca (adelante recto, izquierda, derecha, recto, alto), BOOT o el paro de emergencia lo detienen. Ya probado en el carro. |
| `plantilla/` | Base para programas nuevos. Trae `include/pines_v2.h` con todos los pines de la placa. |

## Abrir

En VS Code: **Archivo > Abrir área de trabajo desde archivo** y elige `RoboUAQ-firmware.code-workspace`.
La primera vez VS Code ofrece instalar las extensiones recomendadas (PlatformIO, tema, iconos, Error Lens y español). Acepta.

## Compilar y subir

### Desde la laptop (VS Code)

Barra de abajo de VS Code (la pone PlatformIO):

- ✓ **Build**: solo compila. No toca la placa.
- → **Upload**: compila y sube al ESP32.
- 🔌 **Serial Monitor**: abre el monitor a 115200.

Si hay varios proyectos abiertos, elige cuál con el selector de entorno de la misma barra (dice `env:esp32doit-devkit-v1 (Prueba PCB)`).

### Desde la Jetson (terminal)

La Jetson ve la placa como `/dev/esp32` (regla udev de la Jetson). Solo `carro-v2` tiene un entorno para eso:

```bash
cd ~/autonomo-v2-pcb/firmware/carro-v2
pio run                      # compila (entorno esp32doit-devkit-v1, el de por defecto)
pio run -e jetson -t upload  # sube por /dev/esp32
pio device monitor -e jetson # ve el serial
```

Cierra cualquier monitor serial antes de subir. Los otros cuatro proyectos no llevan puerto fijo: desde la Jetson pásalo a mano con `--upload-port /dev/esp32`.

## Si no sube

1. Instala el driver del CH340 y revisa que aparezca **USB-SERIAL CH340 (COMx)** en el Administrador de dispositivos.
2. Usa un cable USB-C que pase datos.
3. Pon los 2 jumpers de JP1 (AUTO-RESET). Sin jumpers: BOOT presionado, toque a EN, suelta BOOT y sube.
4. Si sigue fallando, baja `upload_speed` a 115200 en el `platformio.ini`.

## Programa nuevo

Copia `plantilla/`, cámbiale el nombre y agrégala a `folders` en el `.code-workspace`.
