# Firmware de la PCB Autonomo_V2

Todo lo que se carga al ESP32 de la placa va en esta carpeta. Cada programa es un proyecto de PlatformIO.

| Carpeta | Para qué |
|---|---|
| `prueba-pcb/` | Firmware de prueba con menú por serial (115200). Úsalo cada vez que conectes algo nuevo. |
| `plantilla/` | Base para programas nuevos. Trae `include/pines_v2.h` con todos los pines de la placa. |

## Abrir

En VS Code: **Archivo > Abrir área de trabajo desde archivo** y elige `RoboUAQ-firmware.code-workspace`.
La primera vez VS Code ofrece instalar las extensiones recomendadas (PlatformIO, tema, iconos, Error Lens y español). Acepta.

## Compilar y subir

Barra de abajo de VS Code (la pone PlatformIO):

- ✓ **Build**: solo compila. No toca la placa.
- → **Upload**: compila y sube al ESP32.
- 🔌 **Serial Monitor**: abre el monitor a 115200.

Si hay varios proyectos abiertos, elige cuál con el selector de entorno de la misma barra (dice `env:esp32doit-devkit-v1 (Prueba PCB)`).

## Si no sube

1. Instala el driver del CH340 y revisa que aparezca **USB-SERIAL CH340 (COMx)** en el Administrador de dispositivos.
2. Usa un cable USB-C que pase datos.
3. Pon los 2 jumpers de JP1 (AUTO-RESET). Sin jumpers: BOOT presionado, toque a EN, suelta BOOT y sube.
4. Si sigue fallando, baja `upload_speed` a 115200 en el `platformio.ini`.

## Programa nuevo

Copia `plantilla/`, cámbiale el nombre y agrégala a `folders` en el `.code-workspace`.
