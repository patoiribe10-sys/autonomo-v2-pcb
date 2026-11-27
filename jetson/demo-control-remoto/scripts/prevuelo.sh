#!/bin/bash
# prevuelo.sh: lista de comprobacion ANTES de probar el carro con el control y las camaras (solo lectura).
# No cambia nada, no abre las camaras y NO habla con el ESP32.
#   scripts/prevuelo.sh
# Salida: [ OK ] bien, [AVISO] revisar pero se puede seguir, [FALLA] arreglar antes de manejar.
set -u
fallas=0; avisos=0
ok()    { printf '[ OK ] %s\n' "$1"; }
aviso() { printf '[AVISO] %s\n' "$1"; avisos=$((avisos+1)); }
falla() { printf '[FALLA] %s\n' "$1"; fallas=$((fallas+1)); }

echo "=== Servicios que no se tocan ==="
for s in ssh tailscaled NetworkManager bluetooth avahi-daemon nvargus-daemon systemd-timesyncd; do
    [ "$(systemctl is-active $s)" = active ] && ok "$s activo" || falla "$s NO esta activo"
done
n=$(apt-mark showhold | wc -l); [ "$n" -eq 6 ] && ok "hold del kernel: 6 paquetes" || aviso "hold del kernel: $n paquetes (esperaba 6)"

echo; echo "=== Hardware ==="
[ -e /dev/esp32 ] && ok "/dev/esp32 -> $(readlink /dev/esp32)  (ESP32 conectado por USB)" || falla "no existe /dev/esp32: conecta el USB-C de la placa (J1) y revisa la placa prendida"
[ -e /dev/input/js0 ] && ok "control Xbox conectado (/dev/input/js0)" || falla "el control no esta conectado: enciendelo (boton Xbox)"
[ -e /dev/video0 ] && ok "cam0 detectada (/dev/video0)" || falla "cam0 NO detectada (/dev/video0)"
[ -e /dev/video1 ] && ok "cam1 detectada (/dev/video1)" || aviso "cam1 NO detectada (/dev/video1): saldra en negro con 'CAM1 SIN SEÑAL'; cam0 funciona igual"
if grep -q "probe of 10-0010 failed" /var/log/kern.log 2>/dev/null && [ ! -e /dev/video1 ]; then aviso "kern.log: el imx219 10-0010 fallo con -121 (el sensor no contesta; es de cable/conector)"; fi

echo; echo "=== Memoria y procesos ==="
disp=$(awk '/^MemAvailable:/ {printf "%.0f", $2/1024}' /proc/meminfo)
[ "$disp" -ge 3500 ] && ok "memoria disponible: ${disp} MB" || aviso "memoria disponible baja: ${disp} MB (cierra el navegador)"
nav=$(ps -eo comm | grep -c -E "^(chrome|chromium|epiphany|WebKit)"); [ "$nav" -eq 0 ] && ok "ningun navegador abierto en la Jetson" || aviso "hay un navegador abierto en la Jetson ($nav procesos): ciérralo, ocupa memoria"
[ "$(systemctl is-active robocar 2>/dev/null)" = active ] && falla "robocar.service esta corriendo (arranque automatico): para probar a mano o subir firmware, paralo con: sudo systemctl stop robocar"
v=$(pgrep -fc "^(/usr/bin/python3 [^ ]*/(serial_bridge_node|teleop_xbox_node|camaras_node|camara_worker)|/opt/ros/humble/lib/joy/game_controller_node)" || true); [ "${v:-0}" -eq 0 ] && ok "no hay nodos del carro corriendo" || falla "ya hay $v proceso(s) de nodos del carro vivos: ciérralos antes de lanzar"
ss -ltn | grep -q ":8080 " && falla "el puerto 8080 ya esta ocupado" || ok "puerto 8080 libre"

echo; echo "=== Software instalado ==="
I=~/robocar_ws/install/robocar/share/robocar
[ -f "$I/config/sdl_gamecontroller.txt" ] && ok "mapa de SDL propio instalado ($(wc -c < $I/config/sdl_gamecontroller.txt) bytes)" || falla "falta config/sdl_gamecontroller.txt instalado: corre colcon build"
[ -f "$I/launch/control_remoto_launch.py" ] && ok "launch instalado" || falla "falta el launch: corre colcon build"
printf '       yaml del teleop: '; grep -E "^\s+(eje_vel|eje_dir|signo_vel|signo_dir|boton_hombre_muerto|boton_turbo|vel_max):" "$I/config/control_remoto.yaml" 2>/dev/null | awk '{gsub(/#.*/,""); printf "%s%s  ", $1, $2}'; echo
[ "$(systemctl is-active nvargus-daemon)" = active ] && ok "nvargus-daemon PID $(systemctl show nvargus-daemon -p MainPID --value)"

echo; echo "=== Energia y temperatura ==="
echo "       modo nvpmodel: $(nvpmodel -q 2>/dev/null | head -1)"; t=$(( $(cat /sys/class/thermal/thermal_zone1/temp 2>/dev/null || echo 0) / 1000 )); echo "       temperatura: ${t} C"

echo; echo "=== Como verlo desde la laptop (misma red o Tailscale) ==="
ip=$(ip -4 -br a show wlP1p1s0 2>/dev/null | awk '{print $3}' | cut -d/ -f1); ts=$(tailscale ip -4 2>/dev/null | head -1)
[ -n "$ip" ] && echo "       red local : http://$ip:8080    o    http://stitch.local:8080"
[ -n "$ts" ] && echo "       Tailscale : http://$ts:8080"

echo; echo "=== Git ==="
cd ~/robocar_ws && sin=$(git status --short | wc -l); ade=$(git rev-list --count origin/main..HEAD 2>/dev/null)
echo "       cambios sin commit: $sin | commits sin subir: ${ade:-?}"

echo; echo "=== Recordatorios (no se pueden comprobar desde aqui) ==="
echo "       - El ESP32 debe tener el firmware carro-v2 (no prueba-pcb ni demo-recorrido): se sube SOLO cuando Pato diga 'súbelo'."
echo "       - Ruedas al aire la primera vez. El paro de emergencia (lazo J10) debe estar cerrado para que el motor se mueva."
echo "       - Manejo: manten LB; stick izquierdo = velocidad; stick derecho = direccion; RB = turbo."

echo
if [ "$fallas" -eq 0 ]; then echo "=== LISTO: 0 fallas, $avisos aviso(s) ==="; else echo "=== NO LISTO: $fallas falla(s), $avisos aviso(s) ==="; fi
exit $fallas
