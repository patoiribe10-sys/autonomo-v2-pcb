# Demo: control remoto y cámaras

Copia del código de la Jetson que se usó el 26 de noviembre de 2026 para demostrar la placa manejando el carro con un control de Xbox y viendo la cámara en el navegador. La prueba y el video están en [docs/resultado.md](../../docs/resultado.md).

Esta carpeta es una foto fija para el curso. El código vivo, con su historial, está en el repositorio del carro: **https://github.com/patoiribe10-sys/robouaq-carro-autonomo** (copia tomada del commit `870a263`). Si algo cambia allá, esta copia no se actualiza sola.

## Cómo encaja con la placa

```
Control Xbox ──Bluetooth──▶ Jetson Orin Nano ──USB (J1)──▶ ESP32 de la placa ──▶ servo (J3) y motor (J2)
                               │      ▲
                     cámara CSI┘      └── 10 V desde J5 (la placa alimenta a la Jetson)
                               │
                               └──WiFi──▶ navegador de la laptop (puerto 8080)
```

La Jetson nunca mueve el motor directamente. Le manda al ESP32 una línea de texto `V<vel>,S<dir>` (de −100 a 100) y el firmware [`carro-v2`](../../firmware/carro-v2) se encarga del PWM, del servo y de las protecciones. El ESP32 contesta 20 veces por segundo con `v<pulsos/s>,s<dir>,b<mV>,e<estado>`.

## Qué hay aquí

| Carpeta | Qué es |
|---|---|
| `robocar_interfaces/msg/` | Los dos mensajes propios de ROS 2: `ComandoCarro` (velocidad y dirección) y `EstadoCarro` (lo que reporta el ESP32) |
| `robocar/robocar/teleop_xbox_node.py` | Convierte el control en comandos. LB mantenido = hombre muerto; stick izquierdo = velocidad; stick derecho = dirección; RB = turbo |
| `robocar/robocar/serial_bridge_node.py` | Habla con el ESP32 por `/dev/esp32`. Si deja de recibir comandos manda `V0,S0`, y si se desconecta el USB se reconecta solo |
| `robocar/robocar/camaras_node.py` y `camara_worker.py` | Página web en el puerto 8080 con las cámaras (MJPEG), el estado del carro y la batería. Cada cámara corre aparte: si una falla, la otra sigue |
| `robocar/robocar/cierre.py` | Cierre ordenado de los nodos (para que el puente siempre se despida con `V0,S0`) |
| `robocar/launch/control_remoto_launch.py` | Levanta los cuatro nodos |
| `robocar/config/control_remoto.yaml` | Todos los parámetros: índices del control, límites de velocidad, rampas, resolución y fps de la web |
| `robocar/config/sdl_gamecontroller.txt` | Mapeo propio del control Xbox por Bluetooth (el de fábrica de SDL lee mal el stick derecho en la Jetson) |
| `systemd/robocar.service` y `scripts/arranque_carro.sh` | Arranque automático: al prender la Jetson se levanta todo sin entrar por SSH |
| `scripts/` | Herramientas de la prueba: calibrar el control, verificarlo, revisar el arranque y el chequeo previo |

## Seguridad

- Sin LB apretado el carro no se mueve. Al soltarlo frena aunque el stick siga empujado.
- Velocidad limitada a 30 % (60 % con turbo) y 20 % en reversa.
- Si el puente no recibe comandos en 0.3 s manda `V0,S0`. Si el ESP32 no recibe nada en 300 ms, frena por su cuenta.
- El paro de emergencia de la placa (J10) corta la batería del motor por hardware, sin depender del software.

## Cómo se corre

En la Jetson (Ubuntu 22.04, ROS 2 Humble), dentro de un workspace con estos dos paquetes:

```bash
colcon build --packages-select robocar_interfaces robocar
source install/setup.bash
ros2 launch robocar control_remoto_launch.py
```

Después se abre `http://<ip de la Jetson>:8080` en cualquier navegador de la misma red. Con el servicio instalado no hace falta nada de esto: se prende la placa, se espera menos de un minuto y ya responden la web y el control.

```bash
sudo systemctl status robocar      # ver si está corriendo
journalctl -u robocar -f           # ver el log en vivo
sudo systemctl stop robocar        # pararlo (antes de subir firmware al ESP32)
sudo systemctl disable --now robocar   # que ya no arranque solo
```

Las rutas de los scripts y del servicio suponen el usuario `patoih` y el workspace en `~/robocar_ws`.
