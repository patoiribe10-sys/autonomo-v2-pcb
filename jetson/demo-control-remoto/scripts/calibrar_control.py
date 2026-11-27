#!/usr/bin/env python3
"""calibrar_control.py: calibracion GUIADA del control de Xbox (BLE, 045e:0b13).

Te pide cada control por nombre ("stick derecho a la izquierda", "LB", "gatillo derecho"...),
espera a que lo muevas y guarda que eje o boton cambio y con que signo. Mide a la vez:
  * evdev: lo que reporta el kernel (la verdad: codigos ABS_* y BTN_* reales)
  * /joy:  lo que publica game_controller_node despues del mapeo de SDL
y compara las dos. Si SDL mapea mal este control, propone un SDL_GAMECONTROLLERCONFIG propio.

Uso (en una terminal de verdad, con el control prendido):
    source /opt/ros/humble/setup.bash
    python3 ~/robocar_ws/scripts/calibrar_control.py                # medicion guiada
    python3 ~/robocar_ws/scripts/calibrar_control.py --hipotesis    # sin mover nada: calcula la propuesta y la compara con SDL
    python3 ~/robocar_ws/scripts/calibrar_control.py --sdl-propio   # repite la medicion usando la propuesta (verificacion)
    python3 ~/robocar_ws/scripts/calibrar_control.py --solo-evdev   # sin ROS

Salida: ~/robocar_ws/config/control_mapeo_medido.yaml y
        ~/robocar_ws/src/robocar/config/sdl_gamecontroller.propuesta.txt
"""
import argparse
import os
import re
import select
import signal
import struct
import subprocess
import sys
import threading
import time

import yaml

try:
    import evdev
    from evdev import ecodes
except ImportError:
    sys.exit('Falta la libreria evdev (sudo apt install python3-evdev).')

RAIZ = os.path.expanduser('~/robocar_ws')
SALIDA_YAML = os.path.join(RAIZ, 'config', 'control_mapeo_medido.yaml')
SALIDA_SDL = os.path.join(RAIZ, 'src', 'robocar', 'config', 'sdl_gamecontroller.propuesta.txt')
HAT_MIN, HAT_MAX = ecodes.ABS_HAT0X, ecodes.ABS_HAT3Y          # 16..23: SDL los trata como hats
UMBRAL_EVDEV = 0.35        # fraccion del recorrido para dar un eje por movido
UMBRAL_JOY = 0.30
VENTANA_S = 2.5

# (id, texto, tipo)  tipo: reposo | eje | boton | opcional
PASOS = [
    ('reposo', 'SUELTA TODO: no toques el control (miro como descansan los ejes)', 'reposo'),
    ('izq_izq', 'Stick IZQUIERDO hacia la IZQUIERDA, a fondo', 'eje'),
    ('izq_der', 'Stick IZQUIERDO hacia la DERECHA, a fondo', 'eje'),
    ('izq_arr', 'Stick IZQUIERDO hacia ARRIBA, a fondo', 'eje'),
    ('izq_aba', 'Stick IZQUIERDO hacia ABAJO, a fondo', 'eje'),
    ('der_izq', 'Stick DERECHO hacia la IZQUIERDA, a fondo', 'eje'),
    ('der_der', 'Stick DERECHO hacia la DERECHA, a fondo', 'eje'),
    ('der_arr', 'Stick DERECHO hacia ARRIBA, a fondo', 'eje'),
    ('der_aba', 'Stick DERECHO hacia ABAJO, a fondo', 'eje'),
    ('lt', 'Gatillo IZQUIERDO (LT), apretado a fondo', 'eje'),
    ('rt', 'Gatillo DERECHO (RT), apretado a fondo', 'eje'),
    ('lb', 'Boton LB (el bumper de arriba a la IZQUIERDA)', 'boton'),
    ('rb', 'Boton RB (el bumper de arriba a la DERECHA)', 'boton'),
    ('a', 'Boton A (el de ABAJO)', 'boton'),
    ('b', 'Boton B (el de la DERECHA)', 'boton'),
    ('x', 'Boton X (el de la IZQUIERDA)', 'boton'),
    ('y', 'Boton Y (el de ARRIBA)', 'boton'),
    ('ver', 'Boton VER (los dos cuadritos, a la izquierda del logo)', 'boton'),
    ('menu', 'Boton MENU (las tres rayas, a la derecha del logo)', 'boton'),
    ('xbox', 'Boton del LOGO Xbox (el del centro)  [opcional: s para saltar]', 'opcional'),
    ('ls', 'CLIC del stick IZQUIERDO (presionarlo hacia adentro)', 'boton'),
    ('rs', 'CLIC del stick DERECHO (presionarlo hacia adentro)', 'boton'),
    ('share', 'Boton COMPARTIR (el chiquito del centro, solo Series X)  [opcional]', 'opcional'),
    ('dp_arr', 'Cruceta hacia ARRIBA', 'boton'),
    ('dp_aba', 'Cruceta hacia ABAJO', 'boton'),
    ('dp_izq', 'Cruceta hacia la IZQUIERDA', 'boton'),
    ('dp_der', 'Cruceta hacia la DERECHA', 'boton'),
]

# --- Lo que SE ESPERA de un control Xbox BLE con el kernel 5.15 (hipotesis; la medicion la confirma)
EJES_HIP = {'leftx': ecodes.ABS_X, 'lefty': ecodes.ABS_Y, 'rightx': ecodes.ABS_Z, 'righty': ecodes.ABS_RZ,
            'lefttrigger': ecodes.ABS_BRAKE, 'righttrigger': ecodes.ABS_GAS}
TECLAS_HIP = {'a': 304, 'b': 305, 'x': 307, 'y': 308, 'leftshoulder': 310, 'rightshoulder': 311,
              'back': 314, 'start': 315, 'guide': 316, 'leftstick': 317, 'rightstick': 318, 'misc1': 167}


# =========================================================================== utilidades
def nombre_abs(c):
    n = ecodes.ABS.get(c)
    return n if isinstance(n, str) else f'ABS_{c}'


def nombre_key(c):
    n = ecodes.BTN.get(c) or ecodes.KEY.get(c)
    if isinstance(n, (list, tuple)):
        n = n[0]
    return n or f'KEY_{c}'


def buscar_control():
    for ruta in evdev.list_devices():
        d = evdev.InputDevice(ruta)
        if 'Xbox' in d.name or 'Microsoft' in d.name:
            return d
    return None


def indices_sdl(abs_codes, key_codes):
    """Replica como SDL2 numera ejes y botones en Linux (SDL_sysjoystick.c):
    botones: los codigos >= BTN_MISC (0x100) en orden y luego los menores; ejes: ABS_* en orden, sin los hats."""
    ejes = [c for c in sorted(abs_codes) if not (HAT_MIN <= c <= HAT_MAX)]
    botones = sorted(c for c in key_codes if c >= 0x100) + sorted(c for c in key_codes if c < 0x100)
    return {c: i for i, c in enumerate(ejes)}, {c: i for i, c in enumerate(botones)}


def guid_sdl(info):
    return struct.pack('<8H', info.bustype, 0, info.vendor, 0, info.product, 0, info.version, 0).hex()


def armar_mapeo(guid, nombre, ejes, teclas, dpad, ind_ejes, ind_botones, invertir=None):
    """ejes: {'leftx': code,...}; teclas: {'a': code,...}; dpad: {'dpup': 'h0.1',...} o {'dpup': code (boton)}."""
    invertir = invertir or {}
    partes = []
    for campo in ('a', 'b', 'x', 'y', 'back', 'guide', 'start', 'leftstick', 'rightstick',
                  'leftshoulder', 'rightshoulder', 'misc1'):
        c = teclas.get(campo)
        if c is not None and c in ind_botones:
            partes.append(f'{campo}:b{ind_botones[c]}')
    for campo in ('dpup', 'dpright', 'dpdown', 'dpleft'):
        v = dpad.get(campo)
        if v is None:
            continue
        partes.append(f'{campo}:{v}' if isinstance(v, str) else f'{campo}:b{ind_botones[v]}')
    for campo in ('leftx', 'lefty', 'rightx', 'righty', 'lefttrigger', 'righttrigger'):
        c = ejes.get(campo)
        if c is not None and c in ind_ejes:
            partes.append(f'{campo}:a{ind_ejes[c]}{"~" if invertir.get(campo) else ""}')
    return f'{guid},{nombre},' + ','.join(partes) + ',platform:Linux,'


def parsear_mapeo(s):
    d = {}
    for trozo in s.strip().strip(',').split(',')[2:]:
        if ':' in trozo:
            k, v = trozo.split(':', 1)
            d[k] = v
    return d


CODIGO_SDL = r'''
import ctypes
lib = ctypes.CDLL('libSDL2-2.0.so.0')
lib.SDL_Init(0x200 | 0x2000)
lib.SDL_NumJoysticks()
lib.SDL_IsGameController.argtypes = [ctypes.c_int]
lib.SDL_GameControllerMappingForDeviceIndex.restype = ctypes.c_void_p
lib.SDL_GameControllerMappingForDeviceIndex.argtypes = [ctypes.c_int]
m = lib.SDL_GameControllerMappingForDeviceIndex(0)
print(ctypes.string_at(m).decode() if m else '')
'''


def mapeo_actual_sdl(env=None):
    """Pregunta a la SDL del sistema que mapeo usa para el control 0 (en un hijo: si SDL falla no nos tumba)."""
    try:
        r = subprocess.run([sys.executable, '-c', CODIGO_SDL], capture_output=True, text=True, timeout=15,
                           env={**os.environ, **(env or {})})
        linea = [l for l in r.stdout.splitlines() if l.strip()]
        return linea[-1] if linea else None
    except Exception:
        return None


# =========================================================================== captura
class Estado:
    """Valores actuales y ventana de captura, compartidos entre hilos."""

    def __init__(self, dev):
        self.lock = threading.Lock()
        self.vent = None
        caps = dev.capabilities(absinfo=True)
        self.rango = {c: (i.min, i.max) for c, i in caps.get(ecodes.EV_ABS, [])}
        self.abs = {c: i.value for c, i in caps.get(ecodes.EV_ABS, [])}
        self.teclas = sorted(c for c in dev.capabilities().get(ecodes.EV_KEY, []))
        self.joy_ejes = None
        self.joy_botones = None

    def iniciar_ventana(self):
        with self.lock:
            self.vent = {
                'abs_base': dict(self.abs), 'abs_min': dict(self.abs), 'abs_max': dict(self.abs),
                'teclas': set(),
                'j_base': list(self.joy_ejes) if self.joy_ejes else None,
                'j_min': list(self.joy_ejes) if self.joy_ejes else None,
                'j_max': list(self.joy_ejes) if self.joy_ejes else None,
                'j_botones': set(),
            }

    def cerrar_ventana(self):
        with self.lock:
            v, self.vent = self.vent, None
        return v

    def on_abs(self, code, valor):
        with self.lock:
            self.abs[code] = valor
            v = self.vent
            if v is not None:
                v['abs_min'][code] = min(v['abs_min'].get(code, valor), valor)
                v['abs_max'][code] = max(v['abs_max'].get(code, valor), valor)

    def on_key(self, code, valor):
        with self.lock:
            if self.vent is not None and valor == 1:
                self.vent['teclas'].add(code)

    def on_joy(self, ejes, botones):
        with self.lock:
            self.joy_ejes, self.joy_botones = list(ejes), list(botones)
            v = self.vent
            if v is None:
                return
            if v['j_base'] is None:
                v['j_base'], v['j_min'], v['j_max'] = list(ejes), list(ejes), list(ejes)
            for i, x in enumerate(ejes):
                if i < len(v['j_min']):
                    v['j_min'][i] = min(v['j_min'][i], x)
                    v['j_max'][i] = max(v['j_max'][i], x)
            for i, b in enumerate(botones):
                if b:
                    v['j_botones'].add(i)


def hilo_evdev(dev, est, parar):
    while not parar.is_set():
        try:
            r, _, _ = select.select([dev.fd], [], [], 0.1)
            if not r:
                continue
            for ev in dev.read():
                if ev.type == ecodes.EV_ABS:
                    est.on_abs(ev.code, ev.value)
                elif ev.type == ecodes.EV_KEY:
                    est.on_key(ev.code, ev.value)
        except BlockingIOError:
            continue
        except OSError:
            print('\n  !! Se perdio el control (¿se apago o se durmio?). Enciendelo y vuelve a correr el script.')
            parar.set()
            return


def iniciar_ros(est, parar, env_extra):
    """Arranca game_controller_node (con el SDL_GAMECONTROLLERCONFIG pedido) y se suscribe a /joy."""
    try:
        import rclpy
        from rclpy.executors import SingleThreadedExecutor
        from rclpy.node import Node
        from sensor_msgs.msg import Joy
    except ImportError:
        print('  (no hay ROS en este terminal: hago solo evdev. Corre antes: source /opt/ros/humble/setup.bash)')
        return None
    rclpy.init()
    nodo = Node('calibrar_control')
    nodo.create_subscription(Joy, '/joy', lambda m: est.on_joy(m.axes, m.buttons), 10)
    ejecutor = SingleThreadedExecutor()
    ejecutor.add_node(nodo)
    hilo = threading.Thread(target=ejecutor.spin, name='ejecutor')
    hilo.start()
    time.sleep(1.0)
    if nodo.count_publishers('/joy') > 0:
        print('  !! Ya hay otro nodo publicando /joy (¿un game_controller_node abierto?). Cierralo y vuelve a correr esto.')
        ejecutor.shutdown(); hilo.join(timeout=5.0); nodo.destroy_node(); rclpy.shutdown()
        return 'ocupado'
    env = {**os.environ, **env_extra}
    proc = subprocess.Popen(['/opt/ros/humble/lib/joy/game_controller_node'], env=env, start_new_session=True,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(40):
        time.sleep(0.25)
        if est.joy_ejes is not None:
            break
    return {'proc': proc, 'rclpy': rclpy, 'nodo': nodo, 'ejecutor': ejecutor, 'hilo': hilo}


def cerrar_ros(ros):
    if not isinstance(ros, dict):
        return
    try:
        os.killpg(ros['proc'].pid, signal.SIGINT)
        ros['proc'].wait(timeout=5)
    except Exception:
        try:
            os.killpg(ros['proc'].pid, signal.SIGKILL)
        except Exception:
            pass
    # orden: subprocesos (arriba) -> executor -> hilo -> nodo -> rclpy.shutdown()
    try:
        ros['ejecutor'].shutdown()
        ros['hilo'].join(timeout=5.0)
        ros['nodo'].destroy_node()
        if ros['rclpy'].ok():
            ros['rclpy'].shutdown()
    except Exception:
        pass


# =========================================================================== analisis de un paso
def resumir(est, v):
    """Que cambio durante la ventana: ejes evdev, teclas evdev, ejes y botones de /joy."""
    res = {'evdev_ejes': [], 'evdev_teclas': sorted(v['teclas']), 'joy_ejes': [], 'joy_botones': sorted(v['j_botones'])}
    for c, base in v['abs_base'].items():
        lo, hi = est.rango.get(c, (0, 0))
        umbral = 1 if HAT_MIN <= c <= HAT_MAX else UMBRAL_EVDEV * (hi - lo)
        arriba, abajo = v['abs_max'][c] - base, v['abs_min'][c] - base
        mayor = arriba if abs(arriba) >= abs(abajo) else abajo
        if abs(mayor) >= umbral and abs(mayor) > 0:
            res['evdev_ejes'].append({'codigo': c, 'nombre': nombre_abs(c), 'base': base,
                                      'extremo': base + mayor, 'signo': 1 if mayor > 0 else -1, 'delta': abs(mayor)})
    if v['j_base'] is not None:
        for i, base in enumerate(v['j_base']):
            arriba, abajo = v['j_max'][i] - base, v['j_min'][i] - base
            mayor = arriba if abs(arriba) >= abs(abajo) else abajo
            if abs(mayor) >= UMBRAL_JOY:
                res['joy_ejes'].append({'eje': i, 'base': round(base, 2), 'extremo': round(base + mayor, 2),
                                        'signo': 1 if mayor > 0 else -1})
    res['evdev_ejes'].sort(key=lambda d: -d['delta'] / max(1, est.rango.get(d['codigo'], (0, 1))[1] - est.rango.get(d['codigo'], (0, 0))[0]))
    return res


def describir(res):
    partes = []
    for e in res['evdev_ejes']:
        partes.append(f"evdev {e['nombre']} ({e['codigo']}) {e['base']}→{e['extremo']}")
    for t in res['evdev_teclas']:
        partes.append(f'evdev {nombre_key(t)} ({t})')
    for e in res['joy_ejes']:
        partes.append(f"/joy eje {e['eje']} {e['base']:+.2f}→{e['extremo']:+.2f}")
    for b in res['joy_botones']:
        partes.append(f'/joy boton {b}')
    return ' | '.join(partes) if partes else '(nada)'


def hubo_algo(res):
    return bool(res['evdev_ejes'] or res['evdev_teclas'] or res['joy_ejes'] or res['joy_botones'])


def medir(est, paso):
    pid, texto, tipo = paso
    print(f'\n▶ {texto}')
    while True:
        extra = " ('s' = saltar, 'q' = terminar y guardar)" if tipo != 'reposo' else ''
        r = input(f'   ENTER cuando estés listo{extra}: ').strip().lower()
        if r == 'q':
            return 'q', None
        if r == 's':
            return 's', None
        time.sleep(0.4)
        est.iniciar_ventana()
        print('   ¡YA! mantenlo…', end='', flush=True)
        fin = time.monotonic() + VENTANA_S
        while time.monotonic() < fin:
            time.sleep(0.5)
            print('.', end='', flush=True)
        v = est.cerrar_ventana()
        print(' listo. Suelta.')
        time.sleep(0.5)
        res = resumir(est, v)
        if tipo == 'reposo':
            res['reposo_evdev'] = {nombre_abs(c): est.abs.get(c) for c in est.abs}
            res['reposo_joy'] = [round(x, 2) for x in (est.joy_ejes or [])]
            print('   reposo evdev:', res['reposo_evdev'])
            if est.joy_ejes:
                print('   reposo /joy :', res['reposo_joy'])
            return 'ok', res
        print('   →', describir(res))
        if hubo_algo(res):
            return 'ok', res
        r = input("   No detecté nada. [r] reintentar, [s] saltar: ").strip().lower()
        if r == 's':
            return 's', None


# =========================================================================== conclusiones
def unico(lista, clave):
    return lista[0][clave] if lista else None


def conclusiones(est, dev, medidas, con_joy):
    """De las medidas saca: codigos evdev por control, indices SDL, propuesta de mapeo y parametros del yaml."""
    ind_ejes, ind_botones = indices_sdl(est.abs.keys(), est.teclas)

    def eje_de(pid):
        r = medidas.get(pid)
        if not r or not r['evdev_ejes']:
            return None, None
        d = r['evdev_ejes'][0]
        return d['codigo'], d['signo']

    def tecla_de(pid):
        r = medidas.get(pid)
        return r['evdev_teclas'][0] if r and r['evdev_teclas'] else None

    ejes, invertir, avisos = {}, {}, []
    # (campo SDL, paso que lo mide, signo que SDL espera al empujar en esa direccion)
    for campo, pid, esperado in (('leftx', 'izq_der', 1), ('lefty', 'izq_aba', 1), ('rightx', 'der_der', 1),
                                 ('righty', 'der_aba', 1), ('lefttrigger', 'lt', 1), ('righttrigger', 'rt', 1)):
        c, s = eje_de(pid)
        if c is None:
            avisos.append(f'No medí {pid}: no puedo mapear {campo}.')
            continue
        ejes[campo] = c
        invertir[campo] = (s != esperado)
    # revisiones cruzadas: el lado opuesto debe ser el mismo eje con signo contrario
    for pid_a, pid_b in (('izq_izq', 'izq_der'), ('izq_arr', 'izq_aba'), ('der_izq', 'der_der'), ('der_arr', 'der_aba')):
        ca, sa = eje_de(pid_a)
        cb, sb = eje_de(pid_b)
        if ca is not None and cb is not None and (ca != cb or sa == sb):
            avisos.append(f'{pid_a} y {pid_b} no dieron el mismo eje con signo opuesto ({ca}/{sa} vs {cb}/{sb}).')

    teclas = {}
    for campo, pid in (('a', 'a'), ('b', 'b'), ('x', 'x'), ('y', 'y'), ('back', 'ver'), ('start', 'menu'),
                       ('guide', 'xbox'), ('leftstick', 'ls'), ('rightstick', 'rs'), ('leftshoulder', 'lb'),
                       ('rightshoulder', 'rb'), ('misc1', 'share')):
        t = tecla_de(pid)
        if t is not None:
            teclas[campo] = t

    dpad = {}
    for campo, pid, hat_val in (('dpup', 'dp_arr', 'h0.1'), ('dpdown', 'dp_aba', 'h0.4'),
                                ('dpleft', 'dp_izq', 'h0.8'), ('dpright', 'dp_der', 'h0.2')):
        r = medidas.get(pid)
        if not r:
            continue
        if r['evdev_ejes'] and HAT_MIN <= r['evdev_ejes'][0]['codigo'] <= HAT_MAX:
            dpad[campo] = hat_val
        elif r['evdev_teclas']:
            dpad[campo] = r['evdev_teclas'][0]

    nombre = 'Xbox Wireless Controller (BLE medido)'
    guid = guid_sdl(dev.info)
    propuesta = armar_mapeo(guid, nombre, ejes, teclas, dpad, ind_ejes, ind_botones, invertir)

    # que indices tendria /joy con ese mapeo (orden de game_controller_node)
    orden_botones = ['a', 'b', 'x', 'y', 'back', 'guide', 'start', 'leftstick', 'rightstick', 'leftshoulder',
                     'rightshoulder', 'dpup', 'dpdown', 'dpleft', 'dpright', 'misc1']
    # y que indices tiene /joy HOY (medidos), para quien no quiera tocar SDL
    hoy = {}
    if con_joy:
        for pid in ('izq_arr', 'izq_der', 'der_der', 'der_arr', 'lt', 'rt'):
            r = medidas.get(pid)
            if r and r['joy_ejes']:
                hoy[pid] = {'eje': r['joy_ejes'][0]['eje'], 'signo': r['joy_ejes'][0]['signo']}
        for pid in ('lb', 'rb', 'a', 'b', 'x', 'y', 'ver', 'menu', 'xbox', 'ls', 'rs'):
            r = medidas.get(pid)
            if r and r['joy_botones']:
                hoy[pid] = {'boton': r['joy_botones'][0]}
    return {'guid': guid, 'indices_sdl_ejes': {nombre_abs(c): i for c, i in ind_ejes.items()},
            'indices_sdl_botones': {nombre_key(c): i for c, i in ind_botones.items()},
            'propuesta_sdl': propuesta, 'avisos': avisos, 'joy_hoy': hoy,
            'ejes_evdev': {k: nombre_abs(v) for k, v in ejes.items()},
            'teclas_evdev': {k: nombre_key(v) for k, v in teclas.items()}}


def sugerir_yaml(concl):
    """Parametros de teleop_xbox_node si NO se toca SDL (indices medidos de /joy hoy)."""
    h = concl['joy_hoy']
    if not h:
        return None
    p = {}
    if 'izq_arr' in h:
        p['eje_vel'] = h['izq_arr']['eje']
        p['signo_vel'] = float(h['izq_arr']['signo'])        # arriba = adelante
    if 'der_der' in h:
        p['eje_dir'] = h['der_der']['eje']
        p['signo_dir'] = float(h['der_der']['signo'])        # derecha = +100
    if 'lb' in h:
        p['boton_hombre_muerto'] = h['lb']['boton']
    if 'rb' in h:
        p['boton_turbo'] = h['rb']['boton']
    return p


# =========================================================================== hipotesis (sin mover nada)
def modo_hipotesis(dev, est):
    ind_ejes, ind_botones = indices_sdl(est.abs.keys(), est.teclas)
    print(f'\nControl: {dev.name}  (bus {dev.info.bustype:#x}, {dev.info.vendor:#06x}:{dev.info.product:#06x}, version {dev.info.version:#06x})')
    print('GUID SDL calculado:', guid_sdl(dev.info))
    print('\nEjes que declara el kernel → como los numera SDL (a0, a1…):')
    for c, i in ind_ejes.items():
        print(f'   a{i} = {nombre_abs(c)} ({c})')
    print('Botones que declara el kernel → como los numera SDL (b0, b1…):')
    print('   ' + ', '.join(f'b{i}={nombre_key(c)}' for c, i in sorted(ind_botones.items(), key=lambda kv: kv[1])))
    dpad = {'dpup': 'h0.1', 'dpright': 'h0.2', 'dpdown': 'h0.4', 'dpleft': 'h0.8'}
    hip = armar_mapeo(guid_sdl(dev.info), 'Xbox Wireless Controller (BLE hipotesis)', EJES_HIP, TECLAS_HIP, dpad,
                      ind_ejes, ind_botones)
    actual = mapeo_actual_sdl()
    print('\nMapeo que usa SDL HOY (el de fábrica):\n   ', actual)
    print('\nHipótesis (a confirmar midiendo con el script guiado):\n   ', hip)
    if actual:
        a, h = parsear_mapeo(actual), parsear_mapeo(hip)
        print('\nDiferencias (campo: SDL hoy  →  hipótesis):')
        for k in sorted(set(a) | set(h)):
            if k in ('platform',):
                continue
            if a.get(k) != h.get(k):
                print(f'   {k:14s} {a.get(k, "-"):8s} →  {h.get(k, "-")}')
    os.makedirs(os.path.dirname(SALIDA_SDL), exist_ok=True)
    with open(SALIDA_SDL.replace('.propuesta.txt', '.hipotesis.txt'), 'w') as f:
        f.write(hip + '\n')
    print('\n(Guardé la hipótesis en', SALIDA_SDL.replace('.propuesta.txt', '.hipotesis.txt') + ')')


# =========================================================================== principal
def main():
    ap = argparse.ArgumentParser(description='Calibracion guiada del control de Xbox')
    ap.add_argument('--hipotesis', action='store_true', help='no pide nada: calcula la propuesta y la compara con SDL')
    ap.add_argument('--sdl-propio', action='store_true', help='arranca game_controller_node con la propuesta guardada')
    ap.add_argument('--solo-evdev', action='store_true', help='no usa ROS')
    args = ap.parse_args()

    dev = buscar_control()
    if dev is None:
        sys.exit('❌ No encontré el control. ¿Está prendido y conectado por Bluetooth?')
    import atexit
    atexit.register(dev.close)          # evita un traceback del destructor de evdev al salir
    est = Estado(dev)
    print(f'✅ Control: {dev.name}  ({dev.path})')

    if args.hipotesis:
        modo_hipotesis(dev, est)
        return

    env_extra = {}
    if args.sdl_propio:
        archivo = SALIDA_SDL if os.path.exists(SALIDA_SDL) else SALIDA_SDL.replace('.propuesta.txt', '.hipotesis.txt')
        if not os.path.exists(archivo):
            sys.exit('No hay propuesta guardada. Corre primero la medición normal o con --hipotesis.')
        env_extra['SDL_GAMECONTROLLERCONFIG'] = open(archivo).read().strip()
        print('Usando SDL_GAMECONTROLLERCONFIG de', archivo)

    parar = threading.Event()
    threading.Thread(target=hilo_evdev, args=(dev, est, parar), daemon=True).start()
    ros = None if args.solo_evdev else iniciar_ros(est, parar, env_extra)
    if ros == 'ocupado':
        return
    con_joy = isinstance(ros, dict) and est.joy_ejes is not None
    print('   evdev: sí' + (f"   /joy: sí ({len(est.joy_ejes)} ejes, {len(est.joy_botones)} botones)" if con_joy else '   /joy: no (solo evdev)'))
    print('\nTe voy a pedir cada control. Para cada uno: ENTER, y cuando diga ¡YA! hazlo y mantenlo.')

    medidas = {}
    try:
        for paso in PASOS:
            if parar.is_set():
                break
            estado, res = medir(est, paso)
            if estado == 'q':
                break
            if estado == 'ok':
                medidas[paso[0]] = res
    except (KeyboardInterrupt, EOFError):
        print('\n(interrumpido: guardo lo que alcancé)')
    finally:
        parar.set()
        cerrar_ros(ros)

    if len(medidas) <= 1:
        print('Casi no medí nada; no guardo nada.')
        return
    concl = conclusiones(est, dev, medidas, con_joy)

    print('\n' + '=' * 72 + '\nRESUMEN\n' + '=' * 72)
    print('Ejes del kernel → SDL:', concl['indices_sdl_ejes'])
    print('Botones del kernel → SDL:', concl['indices_sdl_botones'])
    if concl['avisos']:
        print('\nAvisos:')
        for a in concl['avisos']:
            print('  -', a)
    actual = mapeo_actual_sdl() if not args.sdl_propio else None
    print('\nSDL_GAMECONTROLLERCONFIG PROPUESTO (medido con evdev):\n ', concl['propuesta_sdl'])
    if actual:
        a, p = parsear_mapeo(actual), parsear_mapeo(concl['propuesta_sdl'])
        dif = [k for k in sorted(set(a) | set(p)) if k != 'platform' and a.get(k) != p.get(k)]
        print('\nSDL de fábrica difiere de lo medido en:', ', '.join(dif) if dif else 'nada (SDL está bien)')
    yaml_hoy = sugerir_yaml(concl)
    if yaml_hoy:
        print('\nSi NO quieres tocar SDL, estos son los índices que /joy tiene hoy (para control_remoto.yaml):')
        for k, v in yaml_hoy.items():
            print(f'    {k}: {v}')
    if args.sdl_propio and con_joy:
        esperado = {'izq_der': ('eje', 0), 'izq_arr': ('eje', 1), 'der_der': ('eje', 2), 'der_arr': ('eje', 3),
                    'lt': ('eje', 4), 'rt': ('eje', 5), 'a': ('boton', 0), 'b': ('boton', 1), 'x': ('boton', 2),
                    'y': ('boton', 3), 'ver': ('boton', 4), 'xbox': ('boton', 5), 'menu': ('boton', 6),
                    'ls': ('boton', 7), 'rs': ('boton', 8), 'lb': ('boton', 9), 'rb': ('boton', 10)}
        print('\nVerificación con el SDL propio (índices estándar de game_controller_node):')
        todo_ok = True
        for pid, (tipo, idx) in esperado.items():
            h = concl['joy_hoy'].get(pid)
            if h is None:
                continue
            ok = h.get(tipo) == idx
            todo_ok &= ok
            print(f"   {pid:8s} esperado {tipo} {idx:2d}  medido {tipo} {h.get(tipo)}  {'OK' if ok else '<-- NO COINCIDE'}")
        print('\n==> ' + ('El mapeo propio funciona: control_remoto.yaml se queda con sus valores por defecto.'
                          if todo_ok else 'Hay diferencias: revisa las líneas marcadas.'))

    os.makedirs(os.path.dirname(SALIDA_YAML), exist_ok=True)
    salida = {'dispositivo': {'nombre': dev.name, 'bus': dev.info.bustype, 'vendor': dev.info.vendor,
                              'product': dev.info.product, 'version': dev.info.version},
              'con_sdl_propio': bool(args.sdl_propio),
              'conclusiones': concl, 'teleop_si_no_se_toca_sdl': yaml_hoy,
              'mediciones': {k: {kk: vv for kk, vv in v.items()} for k, v in medidas.items()}}
    with open(SALIDA_YAML, 'w') as f:
        yaml.safe_dump(salida, f, allow_unicode=True, sort_keys=False, default_flow_style=None)
    if not args.sdl_propio:
        with open(SALIDA_SDL, 'w') as f:
            f.write(concl['propuesta_sdl'] + '\n')
    print(f'\nGuardé: {SALIDA_YAML}' + ('' if args.sdl_propio else f'\n        {SALIDA_SDL}'))


if __name__ == '__main__':
    codigo = main()
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(int(codigo or 0))
