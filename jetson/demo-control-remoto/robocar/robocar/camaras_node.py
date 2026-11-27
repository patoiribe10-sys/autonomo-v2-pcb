#!/usr/bin/env python3
"""camaras_node: transmite las dos camaras CSI en crudo al navegador (MJPEG) y muestra
el estado del carro en grande.

    http://<ip de la Jetson>:8080/            pagina con las dos camaras y el estado
    http://<ip de la Jetson>:8080/cam0.mjpg   cam0 (ojo de pez, carriles)
    http://<ip de la Jetson>:8080/cam1.mjpg   cam1 (normal, senales)
    http://<ip de la Jetson>:8080/estado.json estado del carro y de cada camara

Cada camara es INDEPENDIENTE (su propio hilo y su propio proceso hijo de captura): si una no
aparece, no abre o se cae, la otra sigue transmitiendo y el nodo no se reinicia.

Reglas:
  * Antes de abrir una camara se revisa que exista su /dev/videoN. Si no existe NO se llama a
    nvarguscamerasrc con ese sensor-id (un sensor ausente puede tumbar al nvargus-daemon y
    arrastrar a la otra camara). Solo se vuelve a revisar si aparecio, cada ~10 s (es barato).
  * Si la camara abrio pero se cae, se reintenta con espera creciente: 2, 4, 8, 16 y 30 s (maximo),
    sin trabar el nodo. La espera vuelve a 2 s cuando la camara estuvo estable 10 s.
  * Si nadie esta viendo una camara, NO se abre ni se codifica nada. Se abre al llegar el primer
    espectador y se cierra 3 s despues de que se va el ultimo.
  * En la web se ven siempre los dos cuadros: el que falla sale en negro con "CAM1 SIN SEÑAL" y el
    motivo corto (no detectada / se cayo, reintentando en N s).
  * Un solo JPEG por cuadro, sin importar cuantas personas lo vean.
  * Solo biblioteca estandar, OpenCV del sistema (con GStreamer) y rclpy. NO instalar opencv-python.
  * Si la Jetson se ahoga con las dos camaras, bajar fps_stream a 10 antes de tocar la resolucion.
"""
import json
import os
import select
import struct
import subprocess
import sys
import threading
import time
import unicodedata
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import cv2
import numpy as np
import rclpy
from rclpy.node import Node

from robocar.cierre import ignorar_senales_de_cierre, perro_guardian
from robocar_interfaces.msg import EstadoCarro

try:
    from rclpy.executors import ExternalShutdownException
except ImportError:  # pragma: no cover
    class ExternalShutdownException(Exception):
        pass

SCRIPT_CAMARA = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'camara_worker.py')
GRACIA_S = 3.0            # tiempo que sigue abierta la camara despues del ultimo espectador
ESPERA_DISPOSITIVO_S = 10.0   # cada cuanto se revisa si aparecio /dev/videoN
BACKOFF_INI_S = 2.0       # primera espera tras una caida
BACKOFF_MAX_S = 30.0      # tope de la espera creciente
ESTABLE_S = 10.0          # si estuvo tantos s transmitiendo, la espera vuelve a BACKOFF_INI_S
ARRANQUE_MAX_S = 25.0     # tiempo maximo para el primer cuadro (abrir + 20 de calentamiento)
SIN_CUADROS_S = 6.0       # una vez andando, si pasan tantos s sin cuadro se reinicia el proceso

MOTIVO_SALIDA = {
    2: 'no se pudo abrir',
    3: 'abre pero no entrega cuadros',
    4: 'se cayó',
}


def siguiente_espera(actual, maximo=BACKOFF_MAX_S):
    """2 -> 4 -> 8 -> 16 -> 30 -> 30 ..."""
    return min(actual * 2.0, maximo)


def sin_acentos(texto):
    return unicodedata.normalize('NFKD', texto).encode('ascii', 'ignore').decode()


def texto_centrado(img, texto, y, escala, color, grosor):
    """Escribe 'texto' centrado en la fila y. Dibuja la Ñ con su tilde: las fuentes de OpenCV no la traen."""
    fuente = cv2.FONT_HERSHEY_SIMPLEX
    partes = texto.split('Ñ')
    anchos = [cv2.getTextSize(p, fuente, escala, grosor)[0][0] for p in partes]
    w_n, h_n = cv2.getTextSize('N', fuente, escala, grosor)[0]
    total = sum(anchos) + w_n * (len(partes) - 1)
    x = max(0, (img.shape[1] - total) // 2)
    for i, p in enumerate(partes):
        if p:
            cv2.putText(img, p, (x, y), fuente, escala, color, grosor, cv2.LINE_AA)
            x += anchos[i]
        if i < len(partes) - 1:
            cv2.putText(img, 'N', (x, y), fuente, escala, color, grosor, cv2.LINE_AA)
            ty = y - h_n - max(3, int(8 * escala))
            d = max(2, int(5 * escala))
            tilde = np.array([[x + int(w_n * .15), ty + d], [x + int(w_n * .38), ty],
                              [x + int(w_n * .62), ty + d], [x + int(w_n * .85), ty]], np.int32)
            cv2.polylines(img, [tilde], False, color, grosor, cv2.LINE_AA)
            x += w_n


class Camara:
    """Una camara CSI independiente. La captura corre en un proceso hijo (camara_worker.py) y
    solo mientras hay espectadores y existe su /dev/videoN."""

    def __init__(self, nombre, sensor_id, ancho, alto, fps_sensor, fps_stream, calidad, log,
                 dispositivo=None, espera_disp_s=ESPERA_DISPOSITIVO_S, backoff_ini=BACKOFF_INI_S,
                 backoff_max=BACKOFF_MAX_S, estable_s=ESTABLE_S, cmd_worker=None, giro=0):
        self.nombre = nombre
        self.giro = int(giro)          # flip-method de nvvidconv (2 = 180 grados)
        self.sensor_id = sensor_id
        self.ancho, self.alto = ancho, alto
        self.fps_sensor = fps_sensor
        self.fps_stream = max(1.0, fps_stream)
        self.calidad = int(calidad)
        self.log = log
        self.dispositivo = dispositivo or f'/dev/video{sensor_id}'
        self.espera_disp_s = espera_disp_s
        self.backoff_ini = backoff_ini
        self.backoff_max = backoff_max
        self.estable_s = estable_s
        self._cmd_worker = cmd_worker            # para pruebas: reemplaza el comando del proceso hijo

        self.cond = threading.Condition()
        self.espectadores = 0
        self.jpeg = None
        self.num_cuadro = 0
        self.fps_real = 0.0
        self.existe = None                       # None = aun no se ha revisado
        self.estado = 'dormida'                  # dormida | no_detectada | abriendo | ok | espera
        self.motivo = ''
        self._reintento_en = None                # monotonic del proximo intento (estado 'espera')
        self._ultimo_espectador = 0.0
        self._t_chequeo = 0.0
        self.lanzamientos = 0                    # cuantas veces se lanzo el proceso hijo
        self._proc_vivo = None                   # el proceso hijo actual (para rematarlo al cerrar si hiciera falta)
        self._parar = False
        self._hilo = threading.Thread(target=self._bucle, name=f'cam-{nombre}', daemon=True)

    # ---------------------------------------------------------------- control
    def iniciar(self):
        self._hilo.start()

    def parar(self):
        with self.cond:
            self._parar = True
            self.cond.notify_all()
        self._hilo.join(timeout=8.0)
        # Garantia para salir sin dejar huerfanos: si el hilo se atoro y el hijo sigue vivo, se remata aqui.
        p = self._proc_vivo
        if p is not None and p.poll() is None:
            self.log.warn(f'{self.nombre}: el proceso de captura no cerro a tiempo; se mata')
            try:
                p.kill()
                p.wait(timeout=3.0)
            except Exception:
                pass

    def matar_hijo(self):
        """Mata el proceso de captura si sigue vivo (lo usa el perro guardian del cierre)."""
        p = self._proc_vivo
        if p is not None and p.poll() is None:
            try:
                p.kill()
            except Exception:
                pass

    @property
    def parando(self):
        return self._parar

    def agregar_espectador(self):
        with self.cond:
            self.espectadores += 1
            self.cond.notify_all()

    def quitar_espectador(self):
        with self.cond:
            self.espectadores = max(0, self.espectadores - 1)
            self._ultimo_espectador = time.monotonic()
            self.cond.notify_all()

    def esperar_cuadro(self, ultimo, timeout):
        """Espera un cuadro nuevo (distinto de 'ultimo'). Regresa (jpeg o None, numero)."""
        with self.cond:
            self.cond.wait_for(lambda: self.num_cuadro != ultimo or self._parar, timeout)
            return self.jpeg, self.num_cuadro

    @property
    def abierta(self):
        return self.estado == 'ok'

    def info(self):
        with self.cond:
            reintento = 0.0
            if self.estado == 'espera' and self._reintento_en is not None:
                reintento = max(0.0, self._reintento_en - time.monotonic())
            return {
                'abierta': self.estado == 'ok',
                'estado': self.estado,
                'motivo': self.motivo,
                'reintento_s': round(reintento, 1),
                'dispositivo': self.dispositivo,
                'existe': self.existe,
                'espectadores': self.espectadores,
                'fps': round(self.fps_real, 1),
                'error': '' if self.estado == 'ok' else self.motivo,
            }

    def placeholder(self):
        """Cuadro NEGRO con 'CAMn SIN SEÑAL' y el motivo corto (o 'abriendo...')."""
        img = np.zeros((self.alto, self.ancho, 3), dtype=np.uint8)
        with self.cond:
            estado, motivo = self.estado, self.motivo
            reintento = 0.0
            if estado == 'espera' and self._reintento_en is not None:
                reintento = max(0.0, self._reintento_en - time.monotonic())
        nombre = self.nombre.upper()
        if estado in ('dormida', 'abriendo'):
            texto_centrado(img, f'{nombre} ABRIENDO...', self.alto // 2, 1.1, (170, 170, 170), 2)
        else:
            texto_centrado(img, f'{nombre} SIN SEÑAL', self.alto // 2 - 10, 1.3, (255, 255, 255), 3)
            texto_centrado(img, sin_acentos(motivo)[:48], self.alto // 2 + 35, 0.7, (200, 200, 200), 1)
            if reintento > 0:
                texto_centrado(img, f'reintento en {int(reintento + 0.5)} s', self.alto // 2 + 70, 0.6,
                               (140, 140, 140), 1)
        ok, jpg = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, 60])
        return jpg.tobytes() if ok else b''

    # ----------------------------------------------------------------- estado
    def _set_estado(self, estado, motivo='', reintento_en=None, limpiar_cuadro=False):
        with self.cond:
            cambio = (estado != self.estado) or (motivo != self.motivo)
            self.estado, self.motivo, self._reintento_en = estado, motivo, reintento_en
            if estado != 'ok':
                self.fps_real = 0.0
            if limpiar_cuadro or (cambio and estado != 'ok'):
                self.jpeg = None
                self.num_cuadro += 1
            self.cond.notify_all()

    def revisar_dispositivo(self):
        """Revisa si existe /dev/videoN (barato). Registra en el log solo los CAMBIOS."""
        existe = os.path.exists(self.dispositivo)
        with self.cond:
            antes, self.existe = self.existe, existe
            self._t_chequeo = time.monotonic()
        if antes is not None and antes != existe:
            if existe:
                self.log.info(f'{self.nombre}: apareció {self.dispositivo}; se abre cuando alguien la vea')
            else:
                self.log.warn(f'{self.nombre}: desapareció {self.dispositivo}')
        return existe

    # ------------------------------------------------------- proceso de captura
    def _comando(self):
        if self._cmd_worker is not None:
            return self._cmd_worker()
        return [sys.executable, SCRIPT_CAMARA,
                '--sensor', str(self.sensor_id), '--ancho', str(self.ancho), '--alto', str(self.alto),
                '--fps-sensor', str(int(self.fps_sensor)), '--fps-stream', str(self.fps_stream),
                '--calidad', str(self.calidad), '--giro', str(self.giro)]

    def _lanzar(self):
        try:
            self.lanzamientos += 1
            self._proc_vivo = subprocess.Popen(self._comando(), stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                               bufsize=0)
            return self._proc_vivo
        except OSError as e:
            self.log.warn(f'{self.nombre}: no pude lanzar el proceso de la cámara: {e}',
                          throttle_duration_sec=30.0)
            return None

    def _detener(self, proc):
        """Cierra el proceso hijo con calma (SIGTERM) y, si no obedece, a la fuerza."""
        try:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=4.0)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=2.0)
        except Exception:
            pass
        try:
            proc.stdout.close()
        except Exception:
            pass

    @staticmethod
    def _ultimo_jpeg(buf):
        """Saca de 'buf' todos los cuadros completos y regresa el mas reciente (o None)."""
        ultimo = None
        while len(buf) >= 4:
            n = struct.unpack('>I', bytes(buf[:4]))[0]
            if n == 0 or n > 5_000_000:      # dato corrupto: descartar todo
                buf.clear()
                break
            if len(buf) < 4 + n:
                break
            ultimo = bytes(buf[4:4 + n])
            del buf[:4 + n]
        return ultimo

    def _bucle(self):
        proc = None
        buf = bytearray()
        espera = self.backoff_ini
        proximo_intento = 0.0
        t_inicio = 0.0
        t_abierta = 0.0                 # cuando llego el primer cuadro de esta sesion
        t_ultimo_cuadro = 0.0
        t_fps = time.monotonic()
        n_fps = 0
        espera_reiniciada = False

        while True:
            with self.cond:
                if self._parar:
                    break
                ver = self.espectadores > 0
                en_gracia = (time.monotonic() - self._ultimo_espectador) < GRACIA_S
            ahora = time.monotonic()

            # 1) ¿aparecio/desaparecio el /dev/videoN? solo si no hay proceso, cada ~10 s
            if proc is None and ahora - self._t_chequeo >= self.espera_disp_s:
                self.revisar_dispositivo()

            # 2) dormida: nadie la ve y no hay proceso -> no se abre ni se codifica nada
            if proc is None and not ver:
                if self.existe is False:
                    if self.estado != 'no_detectada':
                        self._set_estado('no_detectada', f'no detectada ({self.dispositivo})')
                elif self.estado != 'dormida':
                    self._set_estado('dormida', limpiar_cuadro=True)
                with self.cond:
                    self.cond.wait(0.5)
                continue

            # 3) se fue el ultimo espectador y paso la gracia -> cerrar
            if proc is not None and not ver and not en_gracia:
                self._detener(proc)
                proc = None
                buf.clear()
                self._set_estado('dormida', limpiar_cuadro=True)
                self.log.info(f'{self.nombre}: nadie la ve, cámara cerrada')
                continue

            # 4) hay espectadores y no hay proceso: ¿se puede abrir?
            if proc is None:
                if not self.existe:
                    # SIN dispositivo: no se toca nvargus. Solo se espera y se vuelve a revisar.
                    self._set_estado('no_detectada', f'no detectada ({self.dispositivo})')
                    with self.cond:
                        self.cond.wait(0.5)
                    continue
                if ahora < proximo_intento:
                    with self.cond:
                        self.cond.wait(0.2)
                    continue
                self._set_estado('abriendo')
                proc = self._lanzar()
                if proc is None:
                    proximo_intento = time.monotonic() + espera
                    self._set_estado('espera', 'no se pudo lanzar', proximo_intento)
                    espera = siguiente_espera(espera, self.backoff_max)
                    continue
                buf.clear()
                t_inicio = time.monotonic()
                t_abierta = t_ultimo_cuadro = 0.0
                t_fps, n_fps = t_inicio, 0
                espera_reiniciada = False
                continue

            # 5) hay proceso: leer lo que mande
            lista, _, _ = select.select([proc.stdout], [], [], 0.2)
            if lista:
                try:
                    datos = os.read(proc.stdout.fileno(), 262144)
                except OSError:
                    datos = b''
                if datos:
                    buf += datos
            jpg = self._ultimo_jpeg(buf)
            if jpg is not None:
                ahora = time.monotonic()
                t_ultimo_cuadro = ahora
                n_fps += 1
                if ahora - t_fps >= 2.0:
                    self.fps_real = n_fps / (ahora - t_fps)
                    t_fps, n_fps = ahora, 0
                primera = False
                with self.cond:
                    if self.estado != 'ok':
                        primera = True
                    self.estado, self.motivo, self._reintento_en = 'ok', '', None
                    self.jpeg = jpg
                    self.num_cuadro += 1
                    self.cond.notify_all()
                if primera:
                    t_abierta = ahora
                    self.log.info(f'{self.nombre}: cámara abierta ({self.dispositivo}, sensor {self.sensor_id})')
                # estuvo estable el tiempo suficiente: la espera creciente vuelve a empezar
                if not espera_reiniciada and t_abierta and ahora - t_abierta >= self.estable_s:
                    espera = self.backoff_ini
                    espera_reiniciada = True

            # 6) ¿murio el hijo o se quedo mudo?
            codigo = proc.poll()
            ahora = time.monotonic()
            if t_ultimo_cuadro > 0:
                mudo = ahora - t_ultimo_cuadro > SIN_CUADROS_S
            else:
                mudo = ahora - t_inicio > ARRANQUE_MAX_S
            if codigo is not None or mudo:
                if codigo is None:
                    motivo = 'dejó de mandar cuadros'
                elif codigo < 0:
                    motivo = f'se cayó (señal {-codigo})'
                else:
                    motivo = MOTIVO_SALIDA.get(codigo, f'terminó (código {codigo})')
                estuvo_estable = bool(t_abierta) and (ahora - t_abierta) >= self.estable_s
                self._detener(proc)
                proc = None
                buf.clear()
                if estuvo_estable:
                    espera = self.backoff_ini
                proximo_intento = time.monotonic() + espera
                self._set_estado('espera', f'{motivo}, reintentando', proximo_intento, limpiar_cuadro=True)
                self.log.warn(f'{self.nombre}: {motivo}. Reintento en {espera:.0f} s si alguien la sigue viendo',
                              throttle_duration_sec=30.0)
                espera = siguiente_espera(espera, self.backoff_max)

        if proc is not None:
            self._detener(proc)


PAGINA = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Stitch - cámaras y estado</title>
<style>
  :root { color-scheme: dark; }
  body { margin: 0; background: #111; color: #eee; font-family: system-ui, sans-serif; }
  header { display: flex; gap: 16px; padding: 16px; flex-wrap: wrap; }
  .caja { flex: 1 1 320px; border-radius: 14px; padding: 18px 24px; text-align: center; }
  .caja .etq { font-size: 1.1rem; opacity: .85; letter-spacing: .05em; text-transform: uppercase; }
  .caja .val { font-size: clamp(2.6rem, 8vw, 5.5rem); font-weight: 800; line-height: 1.1; }
  .caja .sub { font-size: 1.1rem; opacity: .85; min-height: 1.4em; }
  .ok    { background: #0d5c2b; }
  .aviso { background: #8a5a00; }
  .malo  { background: #8e1b1b; }
  .gris  { background: #3a3a3a; }
  main { display: grid; grid-template-columns: repeat(auto-fit, minmax(340px, 1fr)); gap: 12px; padding: 0 16px 16px; }
  figure { margin: 0; background: #000; border-radius: 10px; overflow: hidden; }
  figcaption { padding: 8px 12px; font-size: .95rem; opacity: .85; background: #1b1b1b; }
  figcaption.mal { color: #ff8a80; opacity: 1; }
  img { width: 100%; display: block; background: #000; min-height: 200px; }
  footer { padding: 0 16px 16px; font-size: .9rem; opacity: .7; }
</style>
</head>
<body>
<header>
  <div id="c_estado" class="caja gris">
    <div class="etq">Estado del carro</div>
    <div id="estado" class="val">...</div>
    <div id="estado_sub" class="sub">&nbsp;</div>
  </div>
  <div id="c_bat" class="caja gris">
    <div class="etq">Batería</div>
    <div id="bat" class="val">...</div>
    <div id="bat_sub" class="sub">&nbsp;</div>
  </div>
</header>
<main>
  <figure><img src="/cam0.mjpg" alt="cam0"><figcaption id="t0">cam0 - ojo de pez (carriles)</figcaption></figure>
  <figure><img src="/cam1.mjpg" alt="cam1"><figcaption id="t1">cam1 - frente (señales)</figcaption></figure>
</main>
<footer id="pie">Las cámaras solo se encienden mientras esta página está abierta. Si una falla, la otra sigue.</footer>
<script>
const ESTADOS = {
  0: ["TODO BIEN", "ok"],
  1: ["PARO DE EMERGENCIA", "malo"],
  2: ["SIN COMANDOS", "aviso"],
  3: ["BATERÍA BAJA", "aviso"]
};
const NOMBRES = ["cam0 - ojo de pez (carriles)", "cam1 - frente (señales)"];
function pinta(id, clase) { document.getElementById(id).className = "caja " + clase; }
function texto(id, t) { document.getElementById(id).textContent = t; }
async function actualiza() {
  try {
    const r = await fetch("/estado.json", {cache: "no-store"});
    const e = await r.json();
    if (!e.conectado) {
      texto("estado", "SIN DATOS"); texto("estado_sub", "el ESP32 no está mandando telemetría"); pinta("c_estado", "gris");
      texto("bat", "-- V"); texto("bat_sub", ""); pinta("c_bat", "gris");
    } else {
      const d = ESTADOS[e.estado] || ["ESTADO " + e.estado, "aviso"];
      texto("estado", d[0]);
      texto("estado_sub", "vel " + e.pulsos_s + " pulsos/s   dir " + e.dir);
      pinta("c_estado", d[1]);
      if (e.bateria_mv === 0) {
        texto("bat", "solo USB"); texto("bat_sub", "sin batería conectada"); pinta("c_bat", "gris");
      } else {
        const v = e.bateria_mv / 1000;
        texto("bat", v.toFixed(1) + " V");
        if (v < 9.9)       { texto("bat_sub", "CRÍTICA: motor apagado"); pinta("c_bat", "malo"); }
        else if (v < 10.5) { texto("bat_sub", "baja: velocidad limitada al 50 %"); pinta("c_bat", "aviso"); }
        else               { texto("bat_sub", "ok"); pinta("c_bat", "ok"); }
      }
    }
    for (const n of [0, 1]) {
      const c = e["cam" + n];
      const cap = document.getElementById("t" + n);
      let t = NOMBRES[n];
      if (c.estado === "ok") { t += "  |  " + c.fps + " fps"; cap.className = ""; }
      else if (c.estado === "abriendo" || c.estado === "dormida") { t += "  |  abriendo…"; cap.className = ""; }
      else {
        t += "  |  SIN SEÑAL: " + c.motivo;
        if (c.reintento_s > 0) t += " (reintento en " + Math.ceil(c.reintento_s) + " s)";
        cap.className = "mal";
      }
      cap.textContent = t;
    }
  } catch (err) {
    texto("estado", "SIN CONEXIÓN"); texto("estado_sub", "la Jetson no responde"); pinta("c_estado", "malo");
    texto("bat", "-- V"); pinta("c_bat", "gris");
  }
}
setInterval(actualiza, 500);
actualiza();
</script>
</body>
</html>
"""


class Manejador(BaseHTTPRequestHandler):
    timeout = 10                      # si un cliente deja de leer, no se queda colgado el hilo

    def log_message(self, formato, *args):
        pass                          # sin ruido en la terminal

    def do_GET(self):
        ruta = self.path.split('?', 1)[0]
        nodo = self.server.nodo
        if ruta in ('/', '/index.html'):
            self._enviar(200, 'text/html; charset=utf-8', PAGINA.encode('utf-8'))
        elif ruta == '/estado.json':
            self._enviar(200, 'application/json', json.dumps(nodo.estado_dict()).encode('utf-8'))
        elif ruta in ('/cam0.mjpg', '/cam1.mjpg'):
            self._stream(nodo.camaras[ruta[1:5]])
        elif ruta == '/favicon.ico':
            self._enviar(204, 'image/x-icon', b'')
        else:
            self._enviar(404, 'text/plain; charset=utf-8', b'No encontrado')

    def _enviar(self, codigo, tipo, cuerpo):
        self.send_response(codigo)
        self.send_header('Content-Type', tipo)
        self.send_header('Content-Length', str(len(cuerpo)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        if cuerpo:
            self.wfile.write(cuerpo)

    def _stream(self, cam):
        self.send_response(200)
        self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=frame')
        self.send_header('Cache-Control', 'no-store, private')
        self.send_header('Pragma', 'no-cache')
        self.end_headers()
        cam.agregar_espectador()
        ultimo = -1
        try:
            while not cam.parando:
                jpg, num = cam.esperar_cuadro(ultimo, 1.0)
                ultimo = num
                if jpg is None:
                    jpg = cam.placeholder()       # sin imagen: cuadro negro "SIN SEÑAL" una vez por segundo
                if not jpg:
                    continue
                self.wfile.write(b'--frame\r\nContent-Type: image/jpeg\r\nContent-Length: '
                                 + str(len(jpg)).encode() + b'\r\n\r\n')
                self.wfile.write(jpg)
                self.wfile.write(b'\r\n')
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, TimeoutError, OSError):
            pass
        finally:
            cam.quitar_espectador()


class CamarasNode(Node):

    def __init__(self):
        super().__init__('camaras_node')
        self.declare_parameter('puerto_http', 8080)
        self.declare_parameter('ancho', 640)
        self.declare_parameter('alto', 480)
        self.declare_parameter('fps_sensor', 30)
        self.declare_parameter('fps_stream', 15.0)        # si se ahoga, bajar a 10.0
        self.declare_parameter('calidad_jpeg', 70)
        self.declare_parameter('sensor_cam0', 0)
        self.declare_parameter('sensor_cam1', 1)
        self.declare_parameter('dev_video_cam0', '/dev/video0')
        self.declare_parameter('dev_video_cam1', '/dev/video1')
        self.declare_parameter('giro_cam0', 2)   # cam0 va montada al reves: 2 = girar 180 grados
        self.declare_parameter('giro_cam1', 0)
        self.declare_parameter('espera_dispositivo_s', ESPERA_DISPOSITIVO_S)
        self.declare_parameter('backoff_ini_s', BACKOFF_INI_S)
        self.declare_parameter('backoff_max_s', BACKOFF_MAX_S)
        self.declare_parameter('edad_max_estado', 1.5)    # s: telemetria mas vieja = sin datos

        g = lambda n: self.get_parameter(n).value
        self.edad_max = float(g('edad_max_estado'))
        self._estado = None
        self._t_estado = 0.0
        self._lock = threading.Lock()
        self.create_subscription(EstadoCarro, '/carro/estado', self._on_estado, 10)

        log = self.get_logger()
        comunes = (int(g('ancho')), int(g('alto')), int(g('fps_sensor')),
                   float(g('fps_stream')), int(g('calidad_jpeg')), log)
        extra = dict(espera_disp_s=float(g('espera_dispositivo_s')), backoff_ini=float(g('backoff_ini_s')),
                     backoff_max=float(g('backoff_max_s')))
        self.camaras = {
            'cam0': Camara('cam0', int(g('sensor_cam0')), *comunes, dispositivo=str(g('dev_video_cam0')), giro=int(g('giro_cam0')), **extra),
            'cam1': Camara('cam1', int(g('sensor_cam1')), *comunes, dispositivo=str(g('dev_video_cam1')), giro=int(g('giro_cam1')), **extra),
        }

        # Estado de cada camara al arrancar, en el log (y sin tocar nvargus)
        for c in self.camaras.values():
            if c.revisar_dispositivo():
                log.info(f'{c.nombre}: {c.dispositivo} detectada (sensor {c.sensor_id}); '
                         f'se abre cuando alguien la vea')
            else:
                log.warn(f'{c.nombre}: {c.dispositivo} NO existe -> cámara no detectada. No se llama a nvargus con '
                         f'el sensor {c.sensor_id}; reviso cada {c.espera_disp_s:.0f} s si aparece. '
                         f'La web la muestra en negro con "{c.nombre.upper()} SIN SEÑAL".')
        for c in self.camaras.values():
            c.iniciar()

        puerto = int(g('puerto_http'))
        self.servidor = ThreadingHTTPServer(('0.0.0.0', puerto), Manejador)
        self.servidor.daemon_threads = True
        self.servidor.nodo = self
        self._hilo_http = threading.Thread(target=self.servidor.serve_forever, name='http', daemon=True)
        self._hilo_http.start()
        log.info(f'Cámaras listas en http://0.0.0.0:{puerto}/ (no se abre ninguna hasta que alguien la vea)')

    def _on_estado(self, msg):
        with self._lock:
            self._estado = msg
            self._t_estado = time.monotonic()

    def estado_dict(self):
        with self._lock:
            m, t = self._estado, self._t_estado
        edad = (time.monotonic() - t) if m is not None else None
        fresco = bool(m is not None and m.conectado and edad is not None and edad <= self.edad_max)
        d = {
            'conectado': fresco,
            'estado': int(m.estado) if (fresco and m) else 255,
            'estado_texto': m.estado_texto if (fresco and m) else 'sin datos',
            'bateria_mv': int(m.bateria_mv) if (fresco and m) else 0,
            'pulsos_s': int(m.pulsos_s) if (fresco and m) else 0,
            'dir': int(m.dir) if (fresco and m) else 0,
            'edad_s': round(edad, 2) if edad is not None else None,
        }
        for nombre, cam in self.camaras.items():
            d[nombre] = cam.info()
        return d

    def cerrar(self):
        try:
            self.servidor.shutdown()
            self.servidor.server_close()
        except Exception:
            pass
        for c in self.camaras.values():
            c.parar()


def main(args=None):
    rclpy.init(args=args)
    nodo = CamarasNode()
    try:
        rclpy.spin(nodo)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        ignorar_senales_de_cierre()      # ros2 launch manda SIGINT dos veces: la 2a no debe cortar el cierre
        # si el cierre se atorara mas de 10 s: matar los procesos de captura y salir a la fuerza
        perro_guardian(10.0, limpiar=lambda: [c.matar_hijo() for c in nodo.camaras.values()])
        nodo.cerrar()                    # servidor web, hilos de camara y procesos hijos, en orden
        nodo.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
        # Ya se cerro todo. Se sale sin correr los destructores estaticos de C++ (OpenCV, rclpy, DDS):
        # a veces abortaban con "terminate called without an active exception" (codigo -6) al cerrar.
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(0)


if __name__ == '__main__':
    main()
