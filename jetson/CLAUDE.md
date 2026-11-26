# Carro autónomo RoboUAQ — contexto para Claude Code en la Jetson

Última actualización: 25-nov-2026. Este archivo reemplaza al CLAUDE.md viejo (el de hace un año, de la placa de KiCad). El viejo quedó como `CLAUDE_viejo.md` por si hace falta consultarlo, pero lo que diga ahí sobre la placa ya no aplica.

---

## Quién y para qué

- Dueño: Alain Iribe Haddad ("Pato"), estudiante de Ingeniería Mecatrónica en la Universidad Anáhuac Querétaro, equipo RoboUAQ.
- Proyecto: carro RC escala 1:10 autónomo para la competencia "Robot Conducción Urbana" (UAQ). La siguiente edición es en **mayo de 2027**.
- Reto: recorrer un circuito urbano en menos de 5 minutos, respetando señales y esquivando obstáculos. Solo se permite visión (cámaras).
- También hay un artículo del proyecto completo, así que todo lo que se pruebe se documenta (fotos, mediciones, decisiones, fallas).

**Orden de trabajo que definió Pato:**
1. PCB v2 y curso → ya terminado.
2. **Pruebas básicas en manual: control de Xbox, sin IA ← estamos aquí.**
3. Después, conducción autónoma con visión.
4. Documentar todo en el camino.

---

## Reglas para trabajar con Pato (respetarlas siempre)

- Responder **en español**. Explicar en sencillo lo que no sea obvio; no da por hecho que entienda todo.
- Textos humanos, que no suenen a IA.
- **Subagentes:** preguntar primero si se usan. Si dice que sí: **Opus para planear y hacer debug, Sonnet para programar y explorar. Nunca Haiku.**
- **NO subir firmware al ESP32 hasta que Pato diga "súbelo".** Compilar sí se puede.
- Commits con `Co-Authored-By: Claude ...` y **sin** la línea `Claude-Session`.
- Prefiere archivos completos listos para usar, no parches con `sed`.
- Probar por partes: servo, luego motor, luego juntos, y hasta después ROS.
- Antes de algo difícil de revertir (borrar, reinstalar, flashear, cambiar configuración del sistema), preguntar.
- La contraseña de la Jetson la escribe Pato; no pedirla ni guardarla.
- Al cerrar ("cierra sesión"): agregar al final de este archivo una entrada con fecha de lo que se hizo y lo que sigue (sin borrar las anteriores), y dar a Pato un prompt de continuación.

---

## Objetivos de esta etapa

1. Jetson al 100 y comunicada con la laptop de Pato (Windows 11, VS Code con PlatformIO).
2. Revisar todo `~/robocar_ws` (código de hace un año, hecho para la placa vieja) y decidir qué se reaprovecha, qué se corrige y qué se reescribe.
3. Reescribir lo necesario:
   - ESP32: C con estructuras y apuntadores (PlatformIO, Arduino-ESP32 3.x).
   - Jetson: Python con ROS 2 Humble, pyserial y el OpenCV del sistema.
4. Flujo laptop → Jetson → ESP32 para programar y probar a la vez: editar desde la laptop (VS Code Remote-SSH), compilar y subir el firmware desde la Jetson (PlatformIO CLI por `/dev/ttyUSB0`), ver serial y logs desde la laptop.
5. **Meta:** mover el carro con el control de Xbox conectado a la Jetson por Bluetooth y ver las dos cámaras por WiFi en el navegador de la laptop.

---

## Jetson

- Jetson Orin Nano, nombre "Stitch", usuario `patoih`. JetPack 6.2 (L4T R36.4.7), Ubuntu 22.04, ROS 2 Humble, Python 3.10.
- **No actualizar Ubuntu a 24.04**: JetPack 6 y ROS 2 Humble son de 22.04.
- Antes tenía IP `172.26.169.39` en la WiFi de la escuela (puede haber cambiado).
- Red por USB-C: debería aparecer en la laptop como `192.168.55.1` (servicio `nv-l4t-usb-device-mode`). El 25-nov no apareció; está pendiente averiguar por qué.
- Alimentación: desde J5 de la PCB v2 (+10 V, medido 9.8 V, no baja con carga). Plug de barril centro positivo. Con la batería abajo de ~11 V se pierde margen. En el banco también puede ir a su eliminador.
- Modo de competencia: `sudo nvpmodel -m 2` y `sudo jetson_clocks` (25 W).
- Control Xbox One: ya estuvo emparejado por Bluetooth (revisar con `bluetoothctl`).

### Software viejo en `~/robocar_ws` (revisar, no confiar)
- Paquete `robocar` con los nodos `teleop_xbox_node`, `serial_bridge_node`, `lane_node`, `detect_node` y `nav_node`; dashboard Flask + SocketIO en el puerto 8080; scripts `calibrate_fisheye.py` y `view_camera.py`; launch files; `PROMPT_CLAUDE_CODE.md`.
- `colcon build` compilaba sin errores y el teleop del Xbox publicaba `/cmd_vel`.
- Calibración de cam0 (ojo de pez) hecha: tablero de 5×7 esquinas interiores, RMS 0.6417 px, en `config/camera_fisheye.yaml`.
- Modos de operación pensados: MANUAL (solo Xbox), OBSERVE (Xbox maneja y la visión mira) y AUTO.
- FSM pensada: IDLE → FOLLOW_LANE → APPROACHING_INTERSECTION → STOPPED_AT_INTERSECTION → EXECUTE_TURN → FINISH.
- **Escrito para la placa de KiCad**: STBY puenteado a mano, UART del header abandonado (TX2 a 0.54 V), comunicación por USB, PWM ×85 sin PID y arrancón a 255 por 150 ms. En la v2 eso cambia (ver abajo).

### Trampas conocidas en la Jetson (costaron mucho aprenderlas)
- **Nunca `pip3 install opencv-python`.** Tapa al OpenCV del sistema y se pierde GStreamer. Si aparece, desinstalarlo.
- Pipeline de cámara que funciona (con 20 cuadros de calentamiento):
  `nvarguscamerasrc sensor-id=0 ! video/x-raw(memory:NVMM),width=640,height=480,format=NV12,framerate=30/1 ! nvvidconv ! video/x-raw,format=BGRx ! videoconvert ! video/x-raw,format=BGR ! appsink sync=false drop=true max-buffers=1`
- Arreglo de ldconfig para GStreamer: `/etc/ld.so.conf.d/000_a_nvidia-tegra.conf` se llama así para ordenarse antes de `000_cuda.conf` (si no, la libnvjpeg de CUDA tapa la de Jetson). No tocarlo.
- El usuario debe estar en el grupo `video` (si no, error de NvBufSurface con las cámaras).
- Driver CH340 (el USB-serial del ESP32) no viene en el kernel: está compilado en `~/CH341SER` y se carga con `cd ~/CH341SER && sudo insmod ch34x.ko` **después de cada reinicio**. Pendiente dejarlo como servicio de systemd.
- `brltty` roba `/dev/ttyUSB0`; ya está desactivado.
- **Abrir el serial siempre con `dsrdtr=False, rtscts=False`** en pyserial. Si no, la línea DTR reinicia al ESP32.
- Librerías instaladas: ultralytics, dt-apriltags, pyserial, smbus2, Flask, Flask-SocketIO.

---

## Hardware del carro

- Chasis 1:10 con diferencial. Dirección Ackermann con servo MG995 (directo, sin PCA9685).
- Motor de tracción: GM25-370 con encoder. Está gastado y lento; cambiarlo es opcional. El candidato es un GM25-370 12 V 330 RPM con encoder (UNIT Electronics).
- Batería LiPo 3S (11.1 V nominal, 12.4 V cargada).
- Cámaras: 2 × IMX219 CSI. cam0 = ojo de pez arriba viendo hacia abajo (carriles); cam1 = normal al frente (señales). Para cam1 falta un cable CSI (adaptador de 15 a 22 pines).

### PCB v2 "Autonomo_V2" (Altium, PCBWay) — la placa actual
100 × 100 mm, 4 capas. Llegó el 23-nov-2026 y ya está montada y probada.

| Bloque | Qué hace |
|---|---|
| Entrada | XT60 → fusible 10 A → switch en P2 → protección de inversión → VBAT. Sin switch o puente en P2 no prende |
| +5V lógica | TPS565201, 5 A |
| +3V3 | AP2112K, para el ESP32 |
| +VJET | TPS54560B, 10 V para la Jetson por J5 |
| +5V servo | TPS54560B propio (~5.04 V) con 1000 µF |
| ESP32 | ESP32-WROOM-32E integrado (no es DevKit) |
| USB | USB-C (J1) con CH340C. JP1 = auto-reset con dos jumpers |
| Motor | TB6612FNG con los canales A y B en paralelo |
| Paro de emergencia | Lazo normalmente cerrado en J10 (3-4). Si se abre, corta solo la batería del motor; servo, ESP32 y Jetson siguen vivos |
| Extras | buzzer (J8), luces (J9, voltaje de batería), tira LED WS2812 (J7), 2 × I2C (J11, J12), LED HB |

Voltajes medidos el 25-nov: VBAT 12.4 V, 3V3 3.3 V, 5V 5.0 V, servo 5.04 V, Jetson 9.8 V.

**Pines del ESP32 (fuente: `firmware/plantilla/include/pines_v2.h` del repo):**

| GPIO | Función |
|---|---|
| 34 / 35 | Encoder A / B |
| 25 | Servo (buffer a 5 V → J3) |
| 23 | PWM del motor |
| 21 / 22 | IN1 / IN2 del motor |
| 19 | STBY del TB6612 (HIGH = habilitado; en la v2 ya tiene pull-up) |
| 16 / 17 | UART2 RX / TX → J4 (para después) |
| 18 | HB hacia la Jetson (J4.4) |
| 36 | VBAT por divisor 100k/22k: V = mV × 5.545 |
| 39 | Paro por ADC, mismo divisor: > 5 V = paro activo |
| 27 | START (LOW = presionado) |
| 0 | BOOT (se puede leer como botón) |
| 2 | LED HB |
| 13 | Buzzer |
| 14 | Luces |
| 26 | Tira LED |
| 32 / 33 | I2C SDA / SCL |

**Servo: 1190 µs izquierda, 1360 centro, 1730 derecha. Nunca mandar 1100: se fuerza contra el tope.**

ESP32Servo: llamar `ESP32PWM::allocateTimer(0)` antes de `ledcAttach` del motor (conflicto de timers).

### Cómo se conecta la Jetson con el ESP32
- **Ahora:** cable USB de la Jetson al USB-C J1 de la placa → `/dev/ttyUSB0`, 115200.
- **Después:** J4 al header de 40 pines de la Jetson → `/dev/ttyTHS1` (Serial2 del ESP32). J4.1 GND → pin 6, J4.2 TX → pin 10, J4.3 RX → pin 8. **Nunca correrlo a los pines 4-6-8-10: el pin 4 es 5 V.**
- Con los jumpers de JP1 puestos se puede programar sin tocar botones, pero el DTR puede reiniciar al ESP32 (ver la regla de `dsrdtr=False`). Programar a mano: BOOT presionado, toque a EN, soltar BOOT.
- Cerrar cualquier monitor serial antes de subir firmware.

### Protocolo Jetson ↔ ESP32 (firmware nuevo `firmware/carro-v2`, compila; falta subirlo y probarlo)
- Jetson → ESP32: `V<vel>,S<dir>\n` con vel y dir de -100 a 100 (vel negativa = reversa; dir -100 = izquierda total, 0 = centro, 100 = derecha total).
- ESP32 → Jetson (~20 Hz): `v<pulsos/s>,s<dir>,b<mV batería>,e<estado>\n` con e = 0 ok, 1 paro de emergencia, 2 timeout, 3 batería baja.
- `P\n` → responde `pong`.
- Si no llega un comando válido en 300 ms, frena y centra (estado 2). Por eso el nodo de la Jetson tiene que mandar comandos seguido (cada ~50–100 ms).
- Batería baja: < 10.5 V pita y limita la velocidad al 50 %; < 9.9 V apaga el motor.
- El firmware viejo usaba solo `V<vel>,S<dir>` y contestaba `v...,s...`; los nodos viejos hay que adaptarlos.

---

## Repositorio

- GitHub: `patoiribe10-sys/autonomo-v2-pcb` (público). En la laptop: `C:\Users\symka\autonomo-v2-pcb`.
- `firmware/`: proyectos de PlatformIO (`platform = espressif32@^8.0.0`, board `esp32doit-devkit-v1`, `upload_speed = 460800`):
  - `plantilla/` con `include/pines_v2.h`
  - `prueba-usb/`, `prueba-pcb/` (menú de pruebas) y `demo-recorrido/` (ya probados en la placa)
  - `carro-v2/`: firmware definitivo del carro (compila; falta subirlo y probarlo). Constantes en `include/config.h`; ENC_SIGNO = -1; batería crítica apaga el motor si pasa 1 s abajo de 9.9 V. Al prender marca e=2 (timeout) hasta el primer comando: es normal
- `docs/` (sitio en GitHub Pages: https://patoiribe10-sys.github.io/autonomo-v2-pcb/), `manual/` (manual interactivo de la placa), `hardware/`, `reporte/`.
- Resultados de pruebas para el artículo: `docs/resultado.md`.
- Config del repo: `Alain Iribe Haddad <patoiribe10-sys@users.noreply.github.com>`, `pull.rebase=false`.
- Plan: clonar el repo en la Jetson para que el firmware viva en un solo lugar y compilarlo ahí con `pip install platformio` (funciona en ARM64).

---

## Plan de trabajo sugerido

1. **Red:** que la laptop vea la Jetson (misma WiFi u hotspot; ssh activo; revisar `nv-l4t-usb-device-mode`). Llave SSH desde la laptop para no escribir la contraseña cada vez.
2. **Revisión de `~/robocar_ws`:** inventario de cada archivo (qué hace, si sirve con la v2 y qué cambiar). Entregarle a Pato una tabla: reaprovechar / corregir / reescribir / borrar.
3. **Flujo:** VS Code Remote-SSH, PlatformIO CLI en la Jetson, repo clonado, driver CH340 como servicio, reglas udev para que el ESP32 sea siempre el mismo puerto (p. ej. `/dev/esp32`).
4. **Prueba sin ROS:** `firmware/carro-v2/tools/prueba_serial.py` desde la Jetson (primero `--solo-direccion`, ruedas al aire).
5. **ROS:** `teleop_xbox_node` → `/cmd_vel` → `serial_bridge_node` (protocolo nuevo, timeout, estado de batería y paro) → ESP32.
6. **Cámaras:** dashboard en el puerto 8080 con las dos cámaras, visto desde el navegador de la laptop.
7. **Documentar:** resultados en `docs/resultado.md`, fotos o video para el artículo.

Pendientes de antes que siguen vigentes: control PID de velocidad en el ESP32, calibrar cam1, calibración de vista de pájaro, ajustar los umbrales HSV de carriles en la pista real, probar AprilTags (familia 36h11, IDs 0–5 para las seis señales: no_pasar, sin_salida, vuelta_derecha, vuelta_izquierda, siga_de_frente, alto), alto obligatorio de 3 s antes de cada intersección, y construir la pista reducida de 5 × 6 m.

---

## Bitácora de sesiones

(Agregar al final, con fecha, cada vez que Pato diga "cierra sesión".)

### 25-nov-2026
- La PCB v2 ya está en el carro y probada con batería; el carro se movió con `demo-recorrido`.
- La Jetson se alimenta desde J5 sin problema, pero la laptop no la vio por USB-C. Se conectó monitor y teclado para configurarla.
- Se subió a GitHub el commit de la prueba con batería (`f7736d4`).
- Se empezó el firmware `carro-v2` (C con estructuras y apuntadores).
- Siguiente: red y SSH, revisión de `~/robocar_ws`, flujo de trabajo y manejo con el Xbox.
