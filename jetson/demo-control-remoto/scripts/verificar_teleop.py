#!/usr/bin/env python3
"""verificar_teleop.py: verificacion GUIADA del teleop con el control real (sin ESP32, sin puente).

Arranca game_controller_node (con el SDL_GAMECONTROLLERCONFIG propio si existe
config/sdl_gamecontroller.txt) y teleop_xbox_node, y mira /carro/cmd mientras tu mueves el control.
NO arranca el puente serial: no se manda nada al ESP32.

Te pide cada accion, tu das ENTER, haces la accion y la mantienes ~3 s, y el script dice PASA o FALLA
con los valores medidos y que parametro de control_remoto.yaml cambiar si algo sale al reves.

Uso (en una terminal de verdad, con el control prendido):
    source /opt/ros/humble/setup.bash && source ~/robocar_ws/install/setup.bash
    python3 ~/robocar_ws/scripts/verificar_teleop.py
    python3 ~/robocar_ws/scripts/verificar_teleop.py --solo-reposo     # sin tocar el control (lo corre Claude)
"""
import argparse
import os
import signal
import subprocess
import sys
import threading
import time

import rclpy
from ament_index_python.packages import get_package_share_directory
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from sensor_msgs.msg import Joy

from robocar_interfaces.msg import ComandoCarro

VENTANA_S = 3.0


class Vigia(Node):
    def __init__(self):
        super().__init__('verificar_teleop')
        self.lock = threading.Lock()
        self.cmds = []          # (t, vel, dir)
        self.joys = []          # (t, ejes, botones): lo que llego por /joy, para explicar cada paso
        self.n_joy = 0
        self.create_subscription(ComandoCarro, '/carro/cmd', self._cmd, 10)
        self.create_subscription(Joy, '/joy', self._joy, 10)

    def _cmd(self, m):
        with self.lock:
            self.cmds.append((time.monotonic(), m.vel, m.dir))

    def _joy(self, m):
        with self.lock:
            self.n_joy += 1
            self.joys.append((time.monotonic(), list(m.axes), list(m.buttons)))
            if len(self.joys) > 4000:
                del self.joys[:1000]

    def ventana(self, seg):
        """Devuelve los (vel, dir) publicados durante los proximos 'seg' segundos."""
        t0 = time.monotonic()
        time.sleep(seg)
        with self.lock:
            return [(v, d) for t, v, d in self.cmds if t >= t0]


NOMBRES_EJES = ['LX', 'LY', 'RX', 'RY', 'LT', 'RT']


def resumen_joy(muestras):
    """Que llego por /joy durante la ventana: ejes que se movieron y botones apretados."""
    if not muestras:
        return '/joy durante la ventana: no llego nada'
    ejes = [m[1] for m in muestras]
    botones = [m[2] for m in muestras]
    partes = []
    for i in range(len(ejes[0])):
        lo, hi = min(e[i] for e in ejes), max(e[i] for e in ejes)
        if hi - lo >= 0.3:
            partes.append(f"eje {i} ({NOMBRES_EJES[i] if i < len(NOMBRES_EJES) else '?'}) {lo:+.2f}..{hi:+.2f}")
    apretados = sorted({i for b in botones for i, v in enumerate(b) if v})
    return ('/joy durante la ventana: ' + ('; '.join(partes) if partes else 'NINGUN eje se movio')
            + f' | botones apretados: {apretados or "ninguno"}' + ('' if 9 in apretados else '  (LB = boton 9 NO se apreto)'))


def lanzar(cmd, env=None):
    return subprocess.Popen(cmd, env={**os.environ, **(env or {})}, start_new_session=True,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def matar(p):
    try:
        os.killpg(p.pid, signal.SIGINT)
        p.wait(timeout=5)
    except Exception:
        try:
            os.killpg(p.pid, signal.SIGKILL)
        except Exception:
            pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--solo-reposo', action='store_true', help='solo revisa el reposo (no pide mover nada)')
    a = ap.parse_args()

    compartido = get_package_share_directory('robocar')
    yaml = os.path.join(compartido, 'config', 'control_remoto.yaml')
    sdl = os.path.join(compartido, 'config', 'sdl_gamecontroller.txt')
    env = {}
    if os.path.exists(sdl):
        env['SDL_GAMECONTROLLERCONFIG'] = open(sdl).read().strip()
        print('Usando el SDL_GAMECONTROLLERCONFIG propio:', sdl)
    else:
        print('(sin sdl_gamecontroller.txt: se usa el mapeo de fábrica de SDL)')

    rclpy.init()
    vigia = Vigia()
    ejecutor = SingleThreadedExecutor()
    ejecutor.add_node(vigia)
    hilo_ros = threading.Thread(target=ejecutor.spin, name='ejecutor')
    hilo_ros.start()

    def cerrar_ros():
        """Orden de cierre: (los subprocesos ya se pararon) executor -> hilo -> nodo -> rclpy.
        Si rclpy.shutdown() corre con el hilo todavia girando, el proceso aborta ("terminate called...")."""
        ejecutor.shutdown()
        hilo_ros.join(timeout=5.0)
        try:
            vigia.destroy_node()
        except Exception:
            pass
        if rclpy.ok():
            rclpy.shutdown()

    time.sleep(0.5)
    if vigia.count_publishers('/joy') > 0 or vigia.count_publishers('/carro/cmd') > 0:
        print('!! Ya hay nodos publicando /joy o /carro/cmd (¿un launch abierto?). Ciérralos y repite.')
        cerrar_ros()
        return 1

    procesos = [
        lanzar(['/opt/ros/humble/lib/joy/game_controller_node', '--ros-args', '--params-file', yaml], env),
        lanzar([os.path.expanduser('~/robocar_ws/install/robocar/lib/robocar/teleop_xbox_node'),
                '--ros-args', '--params-file', yaml]),
    ]
    resultados = []

    def chk(nombre, ok, detalle, pista=''):
        resultados.append(ok)
        print(f"   [{'PASA ' if ok else 'FALLA'}] {nombre}: {detalle}" + (f"\n          -> {pista}" if (not ok and pista) else ''),
              flush=True)

    try:
        time.sleep(3.0)
        print('\n== Reposo (no toques el control) ==')
        with vigia.lock:
            n0 = vigia.n_joy
        w = vigia.ventana(2.0)
        with vigia.lock:
            n1 = vigia.n_joy
        chk('llega /joy', n1 - n0 >= 20, f'{n1 - n0} mensajes en 2 s (esperado ~40)',
            'el control no está conectado o game_controller_node no lo ve')
        chk('/carro/cmd llega a ~20 Hz', len(w) >= 30, f'{len(w)} mensajes en 2 s')
        chk('en reposo manda 0,0', len(w) > 0 and all(x == (0, 0) for x in w), f'valores distintos: {sorted(set(w))[:4]}',
            'algún eje o botón está activo en reposo: el mapeo está mal (corre calibrar_control.py)')

        if not a.solo_reposo:
            def paso(texto, evalua):
                print(f'\n▶ {texto}')
                r = input("   ENTER cuando estés listo (s = saltar): ").strip().lower()
                if r == 's':
                    return
                time.sleep(0.3)
                print('   ¡YA! mantenlo…', flush=True)
                t_ini = time.monotonic()
                w = vigia.ventana(VENTANA_S)
                print('   suelta.')
                with vigia.lock:
                    muestras = [j for j in vigia.joys if j[0] >= t_ini]
                print('   ' + resumen_joy(muestras))
                time.sleep(0.8)
                if not w:
                    chk('hay datos', False, 'no llegó nada de /carro/cmd')
                    return
                evalua(w)

            def sin_lb(w):
                chk('sin LB NO se mueve', all(x == (0, 0) for x in w), f'max vel {max(abs(v) for v, _ in w)}, max dir {max(abs(d) for _, d in w)}',
                    'el botón de hombre muerto (boton_hombre_muerto) no es el que crees, o hay otro botón que cuenta como LB')

            def adelante(w):
                vmax = max(v for v, _ in w)
                chk('LB + stick izquierdo ARRIBA da velocidad positiva ~30', 25 <= vmax <= 32, f'vel máx {vmax}',
                    'si sale negativa: signo_vel: -1.0; si es 0: revisa eje_vel y boton_hombre_muerto en control_remoto.yaml')

            def reversa(w):
                vmin = min(v for v, _ in w)
                chk('LB + stick izquierdo ABAJO da reversa ~-20', -22 <= vmin <= -15, f'vel mín {vmin}',
                    'si sale positiva, signo_vel está al revés')

            def derecha(w):
                dmax = max(d for _, d in w)
                chk('LB + stick derecho a la DERECHA da dir ~+100', dmax >= 90, f'dir máx {dmax}',
                    'si sale -100, cambia signo_dir a 1.0; si es 0, revisa eje_dir')

            def izquierda(w):
                dmin = min(d for _, d in w)
                chk('LB + stick derecho a la IZQUIERDA da dir ~-100', dmin <= -90, f'dir mín {dmin}',
                    'si sale +100, signo_dir está al revés')

            def turbo(w):
                vmax = max(v for v, _ in w)
                chk('LB + RB + stick ARRIBA llega a ~60 (turbo)', 55 <= vmax <= 62, f'vel máx {vmax}',
                    'si no pasa de 30, boton_turbo no es RB')

            def suelta(w):
                final = w[-15:]
                chk('al soltar LB en movimiento baja a 0,0', all(x == (0, 0) for x in final), f'últimos valores {sorted(set(final))[:3]}',
                    'la rampa de freno no llegó a 0: revisa rampa_freno')

            paso('Mantén el stick izquierdo ARRIBA a fondo SIN apretar LB', sin_lb)
            paso('Mantén LB apretado y el stick izquierdo ARRIBA a fondo', adelante)
            paso('Mantén LB apretado y el stick izquierdo ABAJO a fondo', reversa)
            paso('Mantén LB apretado y el stick DERECHO a la DERECHA a fondo', derecha)
            paso('Mantén LB apretado y el stick DERECHO a la IZQUIERDA a fondo', izquierda)
            paso('Mantén LB + RB apretados y el stick izquierdo ARRIBA a fondo', turbo)
            paso('Apriétalo todo como en el paso anterior (LB + stick arriba) y a la mitad de la ventana SUELTA LB', suelta)
    except (KeyboardInterrupt, EOFError):
        print('\n(interrumpido)')
    finally:
        for p in procesos:          # 1) subprocesos (game_controller_node y teleop), cada uno con su grupo
            matar(p)
        cerrar_ros()                # 2) executor -> hilo -> nodo -> rclpy.shutdown()

    print(f"\n{sum(resultados)} de {len(resultados)} comprobaciones PASAN")
    return 0 if resultados and all(resultados) else 1


if __name__ == '__main__':
    codigo = main()
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(int(codigo or 0))     # sin destructores de C++ (evita 'terminate called...' al salir)
