#!/bin/bash
# arranque_carro.sh: lo que ejecuta robocar.service al prender la Jetson (tambien se puede correr a mano).
#
#   1) Espera, con tope de tiempo, a: una IP de red (WiFi o cable), el Bluetooth encendido y /dev/esp32.
#      Si algo no aparece, SIGUE de todos modos: la red y el control pueden llegar despues, y el puente
#      reintenta solo abrir el ESP32 (cada 2 s). Nunca se queda esperando para siempre.
#   2) Lanza control_remoto_launch.py con el entorno de ROS 2. El mapa SDL propio del control lo pasa el propio
#      launch (config/sdl_gamecontroller.txt), no hace falta ponerlo aqui.
#
# Variables (opcionales):  ROBOCAR_ESPERA_MAX = segundos de tope para la espera (30; 0 = no esperar)
#                          ROS_DOMAIN_ID      = dominio de ROS (0)

ESPERA_MAX="${ROBOCAR_ESPERA_MAX:-30}"
log() { echo "[arranque_carro] $*"; }

# --- entorno de ROS 2 (sus scripts usan variables sin definir: por eso no se usa 'set -u')
source /opt/ros/humble/setup.bash
source "$HOME/robocar_ws/install/setup.bash" || { log "ERROR: falta ~/robocar_ws/install (corre colcon build)"; exit 1; }
export ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-0}"
export PYTHONUNBUFFERED=1                       # que cada linea llegue de inmediato al journal
export RCUTILS_COLORIZED_OUTPUT=0               # sin codigos de color en el journal
export RCUTILS_CONSOLE_OUTPUT_FORMAT='[{severity}] [{name}]: {message}'
export ROS_LOG_DIR=/dev/shm/robocar_ros_log     # los logs de ROS en RAM: no desgastan la microSD
mkdir -p "$ROS_LOG_DIR"

# --- condiciones de arranque
hay_red() {   # IP global en WiFi o cable (no cuentan tailscale0, docker0, l4tbr0 ni usb0: esas existen sin red)
    ip -4 -o addr show scope global 2>/dev/null | awk '{print $2}' | grep -q -E '^(wl|en|eth)'
}
hay_bt()  { [ "$(timeout 3 bluetoothctl show 2>/dev/null | awk '/Powered:/ {print $2}')" = yes ]; }
hay_esp() { [ -e /dev/esp32 ]; }

red=0; bt=0; esp=0
t0=$SECONDS
log "espero red, Bluetooth y /dev/esp32 (tope ${ESPERA_MAX} s)"
while :; do
    [ $red -eq 0 ] && hay_red && { red=1; log "red lista a los $((SECONDS - t0)) s"; }
    [ $bt  -eq 0 ] && hay_bt  && { bt=1;  log "Bluetooth encendido a los $((SECONDS - t0)) s"; }
    [ $esp -eq 0 ] && hay_esp && { esp=1; log "/dev/esp32 listo a los $((SECONDS - t0)) s"; }
    [ $((red + bt + esp)) -eq 3 ] && break
    if [ $((SECONDS - t0)) -ge "$ESPERA_MAX" ]; then
        [ $red -eq 0 ] && log "AVISO: sin red tras ${ESPERA_MAX} s; sigo (la web responde apenas haya red)"
        [ $bt  -eq 0 ] && log "AVISO: Bluetooth apagado tras ${ESPERA_MAX} s; sigo (el control se conecta cuando se pueda)"
        [ $esp -eq 0 ] && log "AVISO: no hay /dev/esp32 tras ${ESPERA_MAX} s; sigo (el puente reintenta cada 2 s)"
        break
    fi
    sleep 1
done

log "lanzando control_remoto_launch.py (dominio ROS $ROS_DOMAIN_ID)"
exec ros2 launch robocar control_remoto_launch.py
