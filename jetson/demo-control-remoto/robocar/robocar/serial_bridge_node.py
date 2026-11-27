#!/usr/bin/env python3
"""serial_bridge_node: puente entre ROS 2 y el ESP32 (firmware carro-v2).

    /carro/cmd (ComandoCarro)  -->  "V<vel>,S<dir>\\n"  -->  ESP32
    /carro/estado (EstadoCarro) <--  "v<pulsos/s>,s<dir>,b<mV>,e<estado>\\n"  <--  ESP32

Reglas que cumple (las del protocolo de carro-v2):
  * Un solo hilo es dueno del puerto serial: abre, escribe, lee y cierra.
  * El puerto se abre con DTR/RTS apagados y dsrdtr=False, rtscts=False. Si no,
    el CH340 reinicia al ESP32 cada vez que se abre.
  * Manda un comando cada 50 ms (el ESP32 frena si pasan 300 ms sin uno valido).
  * Timeout propio: si /carro/cmd no llega en 300 ms (o nunca llego), manda V0,S0.
    Asi, si el teleop se cae, el carro se detiene aunque el ESP32 siga vivo.
  * Si se desconecta el USB, reintenta abrir cada 2 s sin llenar el log.
  * Al cerrar manda V0,S0 tres veces.
"""
import os
import re
import threading
import time

import rclpy
from rclpy.node import Node
import serial

from robocar.cierre import ignorar_senales_de_cierre, perro_guardian
from robocar_interfaces.msg import ComandoCarro, EstadoCarro

try:  # existe en rclpy de Humble en adelante
    from rclpy.executors import ExternalShutdownException
except ImportError:  # pragma: no cover
    class ExternalShutdownException(Exception):
        pass

TELEMETRIA_RE = re.compile(r'^v(-?\d+),s(-?\d+),b(\d+),e(\d+)$')

ESTADO_OK = 0
ESTADO_PARO = 1
ESTADO_TIMEOUT = 2
ESTADO_BAT_BAJA = 3
ESTADO_SIN_DATOS = 255          # no hay telemetria (conectado = false)

TEXTO_ESTADO = {
    ESTADO_OK: 'ok',
    ESTADO_PARO: 'paro de emergencia',
    ESTADO_TIMEOUT: 'timeout',
    ESTADO_BAT_BAJA: 'bateria baja',
    ESTADO_SIN_DATOS: 'sin datos',
}


def recortar(valor, minimo, maximo):
    return max(minimo, min(maximo, valor))


class SerialBridgeNode(Node):

    def __init__(self):
        super().__init__('serial_bridge_node')

        self.declare_parameter('puerto', '/dev/esp32')
        self.declare_parameter('puerto_respaldo', '/dev/ttyUSB0')
        self.declare_parameter('baudios', 115200)
        self.declare_parameter('periodo_envio', 0.05)       # s entre comandos
        self.declare_parameter('timeout_cmd', 0.3)          # s sin /carro/cmd -> V0,S0
        self.declare_parameter('timeout_telemetria', 0.5)   # s sin telemetria -> conectado=false
        # s sin telemetria -> cerrar y reabrir el puerto (el CH340 a veces abre "mudo": 26-nov). 0 = nunca
        self.declare_parameter('reabrir_sin_telemetria_s', 2.0)
        self.declare_parameter('reintento', 2.0)            # s entre intentos de abrir el puerto

        self.puerto = self.get_parameter('puerto').value
        self.puerto_respaldo = self.get_parameter('puerto_respaldo').value
        self.baudios = int(self.get_parameter('baudios').value)
        self.periodo_envio = float(self.get_parameter('periodo_envio').value)
        self.timeout_cmd = float(self.get_parameter('timeout_cmd').value)
        self.timeout_telemetria = float(self.get_parameter('timeout_telemetria').value)
        self.reabrir_sin_tel = float(self.get_parameter('reabrir_sin_telemetria_s').value)
        self.reintento = float(self.get_parameter('reintento').value)

        self._lock = threading.Lock()
        self._vel = 0
        self._dir = 0
        self._t_cmd = None            # time.monotonic() del ultimo /carro/cmd
        self._parar = threading.Event()
        self._cmd_nuevo = threading.Event()   # despierta al hilo del puerto cuando llega un /carro/cmd distinto
        self._ult_envio = None                # (vel, dir) del ultimo V...,S... escrito al puerto

        self.pub_estado = self.create_publisher(EstadoCarro, '/carro/estado', 10)
        self.create_subscription(ComandoCarro, '/carro/cmd', self._on_cmd, 10)

        self._hilo = threading.Thread(target=self._bucle_serial, name='serial_io', daemon=True)
        self._hilo.start()
        self.get_logger().info(
            f'Puente listo: puerto {self.puerto} (respaldo {self.puerto_respaldo}), '
            f'comando cada {self.periodo_envio * 1000:.0f} ms, timeout de comandos '
            f'{self.timeout_cmd * 1000:.0f} ms')

    # ------------------------------------------------------------------ ROS
    def _on_cmd(self, msg):
        with self._lock:
            self._vel = recortar(int(msg.vel), -100, 100)
            self._dir = recortar(int(msg.dir), -100, 100)
            self._t_cmd = time.monotonic()
            if (self._vel, self._dir) != self._ult_envio:
                self._cmd_nuevo.set()             # comando distinto: escribirlo YA, sin esperar el latido

    def _publicar(self, conectado, pulsos=0, dir_=0, mv=0, estado=ESTADO_SIN_DATOS):
        m = EstadoCarro()
        m.conectado = bool(conectado)
        m.pulsos_s = recortar(int(pulsos), -2147483648, 2147483647)
        m.dir = recortar(int(dir_), -100, 100)
        m.bateria_mv = recortar(int(mv), 0, 65535)
        m.estado = recortar(int(estado), 0, 255)
        m.estado_texto = TEXTO_ESTADO.get(m.estado, 'desconocido')
        m.ultima_telemetria = self.get_clock().now().to_msg()
        try:
            self.pub_estado.publish(m)
        except Exception:
            # Al cerrar, rclpy invalida el contexto ANTES de que termine este hilo: publicar falla con
            # "publisher's context is invalid". Durante el cierre eso es normal y no debe matar el hilo
            # (si muriera aqui no llegaria a su despedida V0,S0). Fuera del cierre si se avisa.
            if not self._parar.is_set() and rclpy.ok():
                self.get_logger().error('No pude publicar /carro/estado', throttle_duration_sec=10.0)

    # --------------------------------------------------------------- Serial
    def _abrir(self):
        """Abre el primer puerto que exista. Regresa el objeto Serial o None."""
        candidatos = []
        for p in (self.puerto, self.puerto_respaldo):
            if p and p not in candidatos and os.path.exists(p):
                candidatos.append(p)
        if not candidatos:
            return None
        for p in candidatos:
            try:
                ser = serial.Serial()
                ser.port = p
                ser.baudrate = self.baudios
                ser.timeout = 0            # lecturas sin bloquear
                ser.write_timeout = 0.2
                ser.xonxoff = False
                ser.dsrdtr = False
                ser.rtscts = False
                ser.dtr = False            # antes de open(), para que no se active al abrir
                ser.rts = False
                ser.open()
                self.get_logger().info(f'Puerto abierto: {p}')
                return ser
            except (serial.SerialException, OSError) as e:
                self.get_logger().warn(f'No pude abrir {p}: {e}', throttle_duration_sec=10.0)
        return None

    def _saludar(self, ser):
        """Manda P y espera pong. Si no contesta no es fatal: la telemetria lo dira."""
        # El CH340 puede levantar DTR un instante al abrir y reiniciar al ESP32.
        self._parar.wait(0.5)
        try:
            ser.reset_input_buffer()
            for _ in range(3):
                ser.write(b'P\n')
                fin = time.monotonic() + 0.7
                datos = bytearray()
                while time.monotonic() < fin and not self._parar.is_set():
                    n = ser.in_waiting
                    if n:
                        datos += ser.read(n)
                    if b'pong' in datos:
                        self.get_logger().info('El ESP32 contesto pong')
                        return True
                    time.sleep(0.02)
        except (serial.SerialException, OSError):
            return False
        self.get_logger().warn('El ESP32 no contesto pong; sigo y reviso la telemetria')
        return False

    def _comando_vigente(self, ahora, estado_viejo):
        """Regresa (vel, dir, comando_viejo). Si el comando esta viejo, es 0,0."""
        with self._lock:
            t = self._t_cmd
            vel, dir_ = self._vel, self._dir
        viejo = (t is None) or (ahora - t > self.timeout_cmd)
        if viejo:
            if not estado_viejo:
                self.get_logger().warn(
                    f'No llegan comandos en /carro/cmd ({self.timeout_cmd * 1000:.0f} ms): mando V0,S0')
            return 0, 0, True
        if estado_viejo:
            self.get_logger().info('Volvieron los comandos en /carro/cmd')
        return vel, dir_, False

    def _procesar_lineas(self, buf, estado_prev):
        """Saca lineas completas de buf. Regresa la ultima telemetria valida o None."""
        ultima = None
        while True:
            i = buf.find(b'\n')
            if i < 0:
                break
            linea = bytes(buf[:i]).decode('ascii', errors='ignore').strip()
            del buf[:i + 1]
            m = TELEMETRIA_RE.match(linea)
            if m:
                ultima = tuple(int(g) for g in m.groups())
        if len(buf) > 512:           # basura sin salto de linea
            buf.clear()
        return ultima

    def _bucle_serial(self):
        ser = None
        buf = bytearray()
        t_tel = 0.0                  # monotonic de la ultima telemetria (0 = ninguna)
        t_abierto = 0.0
        siguiente_envio = 0.0
        proximo_intento = 0.0
        ultimo_aviso_desc = 0.0
        estado_prev = None
        cmd_viejo = True
        solo_usb_avisado = False

        try:
            while not self._parar.is_set():
                ahora = time.monotonic()

                # ---- sin puerto: avisar y reintentar
                if ser is None:
                    if ahora - ultimo_aviso_desc >= 1.0:
                        ultimo_aviso_desc = ahora
                        self._publicar(False)
                    if ahora < proximo_intento:
                        self._parar.wait(0.1)
                        continue
                    ser = self._abrir()
                    if ser is None:
                        proximo_intento = time.monotonic() + self.reintento
                        continue
                    buf.clear()
                    t_tel = 0.0
                    estado_prev = None
                    solo_usb_avisado = False
                    self._saludar(ser)
                    t_abierto = time.monotonic()
                    siguiente_envio = t_abierto
                    continue

                try:
                    # ---- escribir el comando (cada periodo_envio)
                    ahora = time.monotonic()
                    por_evento = self._cmd_nuevo.is_set()
                    if por_evento or ahora >= siguiente_envio:
                        if por_evento:
                            # llego un comando distinto: se escribe YA; el latido se cuenta desde este envio
                            self._cmd_nuevo.clear()
                            siguiente_envio = ahora + self.periodo_envio
                        else:
                            siguiente_envio += self.periodo_envio
                            if siguiente_envio < ahora:
                                siguiente_envio = ahora + self.periodo_envio
                        vel, dir_, cmd_viejo = self._comando_vigente(ahora, cmd_viejo)
                        ser.write(f'V{vel},S{dir_}\n'.encode('ascii'))
                        with self._lock:
                            self._ult_envio = (vel, dir_)

                    # ---- leer telemetria
                    n = ser.in_waiting
                    if n:
                        buf += ser.read(n)
                        tel = self._procesar_lineas(buf, estado_prev)
                        if tel is not None:
                            pulsos, d, mv, estado = tel
                            t_tel = time.monotonic()
                            self._publicar(True, pulsos, d, mv, estado)
                            estado_prev = self._avisos(estado, mv, estado_prev)
                            if mv == 0 and not solo_usb_avisado:
                                solo_usb_avisado = True
                                self.get_logger().info(
                                    'El ESP32 reporta b0: solo USB, sin bateria (no es bateria critica)')
                except (serial.SerialException, OSError) as e:
                    self.get_logger().error(f'Se perdio el puerto serial: {e}. Reintento en {self.reintento:.0f} s')
                    try:
                        ser.close()
                    except Exception:
                        pass
                    ser = None
                    proximo_intento = time.monotonic() + self.reintento
                    ultimo_aviso_desc = 0.0
                    continue

                # ---- telemetria vieja: avisar que no hay datos (maximo 1 por segundo)
                ahora = time.monotonic()
                referencia = t_tel if t_tel > 0 else t_abierto
                if ahora - referencia > self.timeout_telemetria and ahora - ultimo_aviso_desc >= 1.0:
                    ultimo_aviso_desc = ahora
                    self._publicar(False)
                    if t_tel > 0:
                        self.get_logger().warn('El ESP32 dejo de mandar telemetria', throttle_duration_sec=5.0)

                # ---- puerto "mudo": abierto pero sin una sola linea de telemetria -> cerrar y reabrir
                if self.reabrir_sin_tel > 0 and ahora - referencia > self.reabrir_sin_tel:
                    self.get_logger().warn(
                        f'Puerto abierto pero sin telemetria desde hace {ahora - referencia:.1f} s: lo cierro y lo reabro')
                    try:
                        ser.write(b'V0,S0\n')
                        ser.close()
                    except Exception:
                        pass
                    ser = None
                    proximo_intento = time.monotonic() + 1.0   # pausa corta: el CH340 se asienta
                    ultimo_aviso_desc = 0.0
                    continue

                self._cmd_nuevo.wait(0.005)   # se despierta antes si llega un comando nuevo
        except Exception as e:  # cualquier error inesperado: no morir en silencio y SIEMPRE despedirse
            try:
                self.get_logger().error(f'El hilo del puerto serial fallo: {type(e).__name__}: {e}')
            except Exception:
                pass

        # ---- cierre: parar el carro
        if ser is not None:
            try:
                for _ in range(3):
                    ser.write(b'V0,S0\n')
                    time.sleep(0.02)
                ser.close()
            except Exception:
                pass

    def _avisos(self, estado, mv, estado_prev):
        if estado != estado_prev:
            self.get_logger().info(
                f'Estado del ESP32: {TEXTO_ESTADO.get(estado, estado)} (bateria {mv / 1000.0:.2f} V)')
        if estado == ESTADO_PARO:
            self.get_logger().warn('PARO DE EMERGENCIA activo en el ESP32', throttle_duration_sec=5.0)
        elif estado == ESTADO_BAT_BAJA:
            self.get_logger().warn(f'Bateria baja: {mv / 1000.0:.2f} V', throttle_duration_sec=10.0)
        return estado

    # --------------------------------------------------------------- Cierre
    def cerrar(self):
        self._parar.set()
        self._hilo.join(timeout=3.0)


def main(args=None):
    rclpy.init(args=args)
    nodo = SerialBridgeNode()
    try:
        rclpy.spin(nodo)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        ignorar_senales_de_cierre()      # ros2 launch manda SIGINT dos veces: la 2a no debe cortar el cierre
        perro_guardian(8.0)              # si el cierre se atorara, salir a la fuerza a los 8 s
        nodo.cerrar()
        nodo.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
