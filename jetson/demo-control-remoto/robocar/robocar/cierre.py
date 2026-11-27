"""Ayuda para cerrar los nodos sin que una segunda senal interrumpa el cierre.

`ros2 launch` (y Ctrl+C en una terminal junto con el launch) mandan SIGINT DOS veces a cada nodo:
la primera inicia el cierre ordenado y la segunda llega en mitad de ese cierre y lo corta con un
KeyboardInterrupt (el nodo muere con codigo -2 sin terminar de despedirse). Tras la primera senal
se ignoran las siguientes: si el cierre se trabara, `ros2 launch` escala solo a SIGTERM y luego SIGKILL.
"""
import os
import signal
import threading
import time


def ignorar_senales_de_cierre():
    for s in (signal.SIGINT, signal.SIGTERM):
        try:
            signal.signal(s, signal.SIG_IGN)
        except (ValueError, OSError):      # fuera del hilo principal
            pass


def perro_guardian(segundos=10.0, limpiar=None, codigo=3):
    """Si el cierre ordenado tarda mas de 'segundos', ejecuta 'limpiar' (por ejemplo matar procesos hijos) y
    sale a la fuerza. Como tras la primera senal se ignoran las siguientes, esto garantiza que un nodo que
    se atore al cerrar no se quede vivo para siempre (ros2 launch tendria que escalar a SIGKILL)."""
    def _vigila():
        time.sleep(segundos)
        try:
            if limpiar is not None:
                limpiar()
        finally:
            os._exit(codigo)
    threading.Thread(target=_vigila, daemon=True, name='perro_guardian').start()
