# carro-v2

Firmware del ESP32 del carro (PCB Autonomo_V2). La Jetson le manda velocidad y dirección, y él maneja el motor y el servo, mide el encoder y vigila la batería y el paro de emergencia. Está escrito en C con estructuras y apuntadores (nada de clases propias), una carpeta por módulo en `src/`:

| Módulo | Qué hace |
|---|---|
| `motor` | Puente H, PWM de 8 bits, rampa de aceleración y zona muerta |
| `direccion` | Servo con movimiento suave y límites 1190 / 1360 / 1680 µs |
| `encoder` | Cuadratura por interrupción, pulsos/s cada 50 ms |
| `protocolo` | Lee `V..,S..`, `P` y `?`; arma la telemetría |
| `seguridad` | Bateria, paro de emergencia y botones |
| `carro` | Junta todo: estado, timeout, LED, buzzer, telemetría |

## Protocolo (115200, líneas con `\n`)

Jetson al ESP32:

- `V<vel>,S<dir>`: vel de -100 a 100 (%, negativo = reversa), dir de -100 (izquierda) a 100 (derecha), 0 = centro. Se recortan si se pasan. Las líneas mal formadas se ignoran.
- `P`: contesta `pong`.
- `?`: imprime el estado en texto legible.

ESP32 a la Jetson, 20 veces por segundo:

```
v<pulsos/s>,s<dir>,b<mV bateria>,e<estado>
```

`e` vale 0 ok, 1 paro de emergencia, 2 timeout, 3 batería baja o crítica. Si hay varios a la vez gana este orden: paro, batería crítica, timeout, batería baja. Con la placa solo por USB reporta `b0`.

El ESP32 escucha por USB (`/dev/esp32`, que apunta a `/dev/ttyUSB0`) y por UART2 (J4, RX16/TX17) al mismo tiempo, y contesta por el puerto del último comando válido. Antes del primer comando contesta por USB.

## Seguridad

- **Timeout:** si no llega un `V..,S..` válido en 300 ms, el motor frena con la rampa y el servo vuelve al centro (`e=2`). Al llegar un comando se recupera solo. Después de encender también está en `e=2` hasta el primer comando. `P` y `?` no cuentan para el timeout.
- **Paro por el lazo de J10:** se lee ESTOP_G por ADC (GPIO 39) con el factor 5.545, igual que el demo y `prueba-pcb`. Más de 5 V calculados = lazo abierto = paro activo: motor a cero sin rampa (`e=1`). Se libera solo cuando se cierra el lazo. Con solo USB marca ~0 V, así que no hay paro.
- **BOOT y START:** BOOT es un paro por software (útil en banco) y se queda hasta que presionas START.
- **Batería:** VBAT en GPIO 36 con promedio móvil. Debajo de 10.5 V por más de 2 s suena el buzzer y la velocidad máxima baja al 50%. Debajo de 9.9 V por más de 1 s se apaga el motor. Las alarmas se quitan arriba de 10.8 V. Si VBAT marca menos de 3 V se considera que solo hay USB y no se hace nada.
- **Motor:** el PWM sube por rampa (de 0 a 255 en unos 0.3 s) y con cualquier velocidad distinta de 0 nunca baja de 60.
- **LED HB:** 1 Hz si todo bien, rápido con paro, timeout o batería crítica.

## Cómo probarlo desde la Jetson

1. Compila y sube. Ruedas al aire la primera vez.
   - **Laptop (Windows):** botón Upload de VS Code o `pio run -t upload`. Usa el entorno `esp32doit-devkit-v1` (el de por defecto) y detecta el puerto solo.
   - **Jetson:** `pio run -e jetson -t upload` y, para ver el serial, `pio device monitor -e jetson`. El entorno `jetson` es el mismo pero con `upload_port` y `monitor_port` en `/dev/esp32`. Cierra cualquier monitor antes de subir.
2. Copia `tools/prueba_serial.py` a la Jetson (necesita `pyserial`).
3. Corre `python3 prueba_serial.py --solo-direccion` para ver solo el servo. Sin la bandera también mueve el motor a 25% por 2 s.
4. A mano: `python3 -m serial.tools.miniterm --dtr 0 --rts 0 /dev/esp32 115200`, escribes `P` y debe contestar `pong`.

Siempre abre el puerto con `dsrdtr=False, rtscts=False` (y DTR/RTS apagados) o el CH340 reinicia al ESP32.

## Constantes que se ajustan

Todas están en `include/config.h`:

- `DIR_ADELANTE` (1 o -1): sentido del motor.
- `ENC_SIGNO` (1 o -1): signo del encoder. Está en -1 porque con el conteo de `prueba-pcb` adelante salía negativo (probado el 25-nov).
- `PWM_MIN_ARRANQUE`, `RAMPA_PWM_PASO`, `RAMPA_PASO_MS`: zona muerta y rampa.
- `SERVO_VEL_US_S`: velocidad del servo (1500 µs/s).
- `TIMEOUT_CMD_MS`, `TELEMETRIA_MS`.
- `BAT_BAJA_MV`, `BAT_CRITICA_MV`, `BAT_VEL_MAX_BAJA` y sus tiempos.
- `ESTOP_UMBRAL_V`.

Los pines están en `include/pines_v2.h` (copia de `plantilla/`, sin cambios).
