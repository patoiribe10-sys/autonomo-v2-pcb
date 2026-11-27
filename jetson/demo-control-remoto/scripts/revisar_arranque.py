#!/usr/bin/env python3
"""revisar_arranque.py: informe (SOLO LECTURA) de como arranco robocar.service en ESTE arranque de la Jetson.

Lee el journal del servicio y arma una linea de tiempo con los segundos desde el inicio del kernel, para contestar:
  - ¿cuanto tardo en responder la web?
  - ¿encontro el control? Si arranco con el control apagado, ¿lo encontro tarde, cuando lo prendiste?
  - ¿conecto el ESP32?, ¿hubo reinicios o errores?
Uso:  python3 ~/robocar_ws/scripts/revisar_arranque.py            (el servicio instalado: journalctl -u robocar -b)
      python3 ~/robocar_ws/scripts/revisar_arranque.py --usuario robocar-prueba   (un servicio transitorio de usuario)
Se puede correr varias veces: antes de prender el control, despues de prenderlo, etc.
"""
import argparse
import re
import subprocess
import urllib.request

LINEA = re.compile(r'^\[\s*([0-9]+\.[0-9]+)\]\s+\S+\s+[^:\[]+(?:\[\d+\])?:\s(.*)$')
EVENTOS = [   # (patron, etiqueta)
    (r'espero red, Bluetooth', 'el script empieza a esperar red / Bluetooth / ESP32'),
    (r'red lista a los', 'red lista'),
    (r'Bluetooth encendido a los', 'Bluetooth encendido'),
    (r'/dev/esp32 listo a los', '/dev/esp32 listo'),
    (r'AVISO:', 'AVISO del script (algo no estaba listo a tiempo)'),
    (r'lanzando control_remoto_launch', 'LANZA el launch'),
    (r'Controller Found', 'CONTROL ENCONTRADO por game_controller_node'),
    (r'Teleop listo', 'teleop listo'),
    (r'No llega /joy', 'teleop: no llega /joy (control apagado o sin conectar)'),
    (r'Volvio /joy', 'teleop: llego /joy'),
    (r'C.maras listas', 'WEB LISTA (camaras_node escuchando en :8080)'),
    (r'No pude abrir', 'puente: no pudo abrir el puerto'),
    (r'Puerto abierto', 'puente: puerto abierto'),
    (r'lo cierro y lo reabro', 'puente: puerto mudo, lo reabre'),
    (r'El ESP32 contesto pong', 'ESP32 contesto pong'),
    (r'Estado del ESP32', 'estado del ESP32'),
]


def sh(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True).stdout


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--usuario', default='', help='nombre de un servicio transitorio de usuario (para probar este script)')
    a = ap.parse_args()
    if a.usuario:
        jc = f'journalctl --user-unit {a.usuario}.service -o short-monotonic --no-pager'
        estado = f'systemctl --user show {a.usuario} -p ActiveState -p NRestarts -p ActiveEnterTimestamp'
    else:
        jc = 'journalctl -u robocar -b -o short-monotonic --no-pager'
        estado = 'systemctl show robocar -p ActiveState -p SubState -p NRestarts -p ActiveEnterTimestamp'
    salida = sh(jc)
    eventos, errores, avisos_raros = [], 0, []
    for l in salida.splitlines():
        m = LINEA.match(l)
        if not m:
            continue
        t, msg = float(m.group(1)), m.group(2)
        if re.search(r'\[ERROR\]|Traceback', msg):
            errores += 1
        for pat, et in EVENTOS:
            if re.search(pat, msg):
                eventos.append((t, et, msg))
                break
    print('=== ARRANQUE:', sh('systemd-analyze 2>/dev/null | head -1').strip() or '(systemd-analyze no disponible)')
    print('=== SERVICIO:', ' | '.join(x for x in sh(estado).split('\n') if x))
    if not eventos:
        print('\nEl journal del servicio no tiene eventos: ¿está instalado y habilitado? (systemctl status robocar)')
        return
    lanza = next((t for t, e, _ in eventos if e.startswith('LANZA')), None)
    print('\n--- Linea de tiempo (segundos desde el inicio del kernel; [+x] = despues de lanzar el launch) ---')
    for t, et, msg in eventos:
        d = f'[{t - lanza:+6.1f}]' if lanza is not None else '        '
        extra = ''
        if et.startswith('estado del ESP32') or et.startswith('AVISO'):
            extra = '  -> ' + msg[msg.find(':') + 2:][:90]
        print(f'{t:8.1f} s {d}  {et}{extra}')

    print('\n--- VEREDICTO ---')
    web = next((t for t, e, _ in eventos if e.startswith('WEB LISTA')), None)
    if web is not None:
        print(f'WEB: quedó lista a los {web:.1f} s del inicio del kernel (no incluye lo que tarde el firmware antes del kernel).')
    try:
        code = urllib.request.urlopen('http://localhost:8080/estado.json', timeout=2).status
    except Exception as e:
        code = f'sin respuesta ({type(e).__name__})'
    print(f'WEB ahora mismo: HTTP {code}')

    encontrados = [t for t, e, _ in eventos if e.startswith('CONTROL ENCONTRADO')]
    sin_joy = [t for t, e, _ in eventos if e.startswith('teleop: no llega')]
    llego = [t for t, e, _ in eventos if e == 'teleop: llego /joy']
    bt = sh('bluetoothctl devices 2>/dev/null').split('\n')
    estado_bt = ''
    for l in bt:
        p = l.split()
        if len(p) >= 2 and p[0] == 'Device':
            info = sh(f'bluetoothctl info {p[1]} 2>/dev/null')
            if 'Xbox' in info:
                estado_bt = ' '.join(x.strip() for x in info.split('\n') if re.match(r'\s*(Paired|Trusted|Connected):', x))
    if not encontrados:
        print('CONTROL: NO ha sido encontrado por game_controller_node en este arranque.')
        print(f'   Bluetooth del control ahora: {estado_bt or "(no se pudo leer)"}')
        print('   · Si dice "Connected: no": el control no se ha conectado (¿lo prendiste? ¿ya pasaron ~10 s?).')
        print('   · Si dice "Connected: yes" y aun no aparece "CONTROL ENCONTRADO" tras ~15 s: el nodo NO detecta controles que')
        print('     aparecen despues de arrancar. Hay que arreglarlo (reiniciar el servicio al conectarse el control).')
    else:
        t = encontrados[0]
        if lanza is not None:
            print(f'CONTROL: encontrado {t - lanza:+.1f} s despues de lanzar el launch.')
        tarde = bool(sin_joy) and sin_joy[0] < t
        if tarde:
            print('   => arrancó SIN control y lo encontró DESPUES (se reconectó tarde): ES LO QUE QUERÍAS PROBAR.')
        else:
            print('   => ya estaba conectado cuando arrancó el servicio (no es la prueba del control apagado).')
        if llego:
            print(f'   /joy llegó a los {llego[-1]:.1f} s.')
        print(f'   Bluetooth del control ahora: {estado_bt or "(no se pudo leer)"}')
    if any(e.startswith('puente: puerto mudo') for _, e, _ in eventos):
        print('ESP32: el puerto abrió "mudo" y el puente lo reabrió solo (conocido; no es falla).')
    if any(e == 'ESP32 contesto pong' for _, e, _ in eventos):
        print('ESP32: contestó pong.')
    elif any(e.startswith('puente: no pudo abrir') for _, e, _ in eventos):
        print('ESP32: el puente no pudo abrir el puerto (¿/dev/esp32? ¿otro programa lo usa?).')
    else:
        print('ESP32: sin pong todavía.')
    reinicios = sh('systemctl show robocar -p NRestarts --value 2>/dev/null').strip() if not a.usuario else '?'
    print(f'REINICIOS del servicio en este arranque: {reinicios or "?"}   |   líneas con ERROR o Traceback: {errores}')


if __name__ == '__main__':
    main()
