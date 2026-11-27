#!/usr/bin/env python3
"""camara_worker: proceso hijo de camaras_node. Abre UNA camara CSI y escribe JPEGs por stdout.

Corre separado del nodo a proposito: si el nvargus-daemon falla (por ejemplo se cae cuando
le falta memoria), la conexion Argus de ESTE proceso queda rota para siempre. Reiniciando
solo este proceso se recupera la camara sin tumbar el nodo ni el servidor web.

Formato de salida (stdout, binario): por cada cuadro, 4 bytes big-endian con la longitud
del JPEG y luego los bytes del JPEG. Los mensajes de error van a stderr.

Codigos de salida: 0 normal (SIGTERM, SIGINT o el nodo cerro el pipe), 2 no abrio la
camara, 3 abrio pero no entrega cuadros, 4 se perdio la imagen.

No depende de ROS. Usa el OpenCV del sistema (con GStreamer): NO instalar opencv-python.
"""
import argparse
import signal
import struct
import sys
import time

import cv2

# Pipeline que funciona en esta Jetson (ver CLAUDE.md), con 20 cuadros de calentamiento
PIPELINE = (
    'nvarguscamerasrc sensor-id={sensor} ! '
    'video/x-raw(memory:NVMM),width={ancho},height={alto},format=NV12,framerate={fps}/1 ! '
    'nvvidconv flip-method={giro} ! video/x-raw,format=BGRx ! videoconvert ! video/x-raw,format=BGR ! '
    'appsink sync=false drop=true max-buffers=1'
)
CUADROS_CALENTAMIENTO = 20


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--sensor', type=int, default=0)
    ap.add_argument('--ancho', type=int, default=640)
    ap.add_argument('--alto', type=int, default=480)
    ap.add_argument('--fps-sensor', type=int, default=30)
    ap.add_argument('--fps-stream', type=float, default=15.0)
    ap.add_argument('--calidad', type=int, default=70)
    ap.add_argument('--giro', type=int, default=0, choices=range(0, 8),
                    help='flip-method de nvvidconv: 0 nada, 2 = girar 180 grados (camara montada al reves)')
    a = ap.parse_args()

    parar = {'si': False}

    def _senal(signum, frame):
        parar['si'] = True

    signal.signal(signal.SIGTERM, _senal)
    signal.signal(signal.SIGINT, _senal)

    pipe = PIPELINE.format(sensor=a.sensor, ancho=a.ancho, alto=a.alto, fps=a.fps_sensor, giro=a.giro)
    cap = cv2.VideoCapture(pipe, cv2.CAP_GSTREAMER)
    if not cap.isOpened():
        print(f'camara {a.sensor}: no abre', file=sys.stderr, flush=True)
        cap.release()
        return 2
    for _ in range(CUADROS_CALENTAMIENTO):
        if parar['si']:
            cap.release()
            return 0
        ok, _ = cap.read()
        if not ok:
            print(f'camara {a.sensor}: no entrega cuadros', file=sys.stderr, flush=True)
            cap.release()
            return 3

    salida = sys.stdout.buffer
    intervalo = 1.0 / max(1.0, a.fps_stream)
    t_enc = 0.0
    codigo = 0
    while not parar['si']:
        ok, frame = cap.read()
        if not ok or frame is None:
            print(f'camara {a.sensor}: se perdio la imagen', file=sys.stderr, flush=True)
            codigo = 4
            break
        ahora = time.monotonic()
        if ahora - t_enc < intervalo * 0.85:
            continue                       # limite de fps: no se codifica este cuadro
            # (el 0.85 evita que el sensor a 30 fps y un limite de 15 se desfasen y queden en 10)
        t_enc = ahora
        ok, jpg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, a.calidad])
        if not ok:
            continue
        datos = jpg.tobytes()
        try:
            salida.write(struct.pack('>I', len(datos)))
            salida.write(datos)
            salida.flush()
        except (BrokenPipeError, OSError):
            break                          # el nodo cerro el pipe: terminar
    cap.release()
    return codigo


if __name__ == '__main__':
    sys.exit(main())
