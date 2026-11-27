#!/usr/bin/env python3
"""teleop_xbox_node: convierte /joy (control de Xbox) en /carro/cmd.

    /joy (sensor_msgs/Joy, de game_controller_node)  -->  /carro/cmd (ComandoCarro)

Manejo:
    LB mantenido  = hombre muerto. Sin LB el carro se detiene y centra la direccion.
    Stick izq. arriba/abajo = velocidad (adelante / reversa)
    Stick der. izquierda/derecha = direccion
    RB (con LB) = turbo

Seguridad:
  * Publica SIEMPRE a 20 Hz (el puente frena si dejan de llegar comandos).
  * Si /joy deja de llegar (control apagado o desconectado) manda 0,0 de golpe.
  * La velocidad sube con rampa (maximo rampa_acel por ciclo) para que no haya tirones
    al soltar y volver a apretar el hombre muerto con el stick a fondo. Al frenar la
    rampa es mas rapida (rampa_freno). El firmware tambien trae su propia rampa.
  * Por el cable solo viajan porcentajes (-100..100). El paso a microsegundos del
    servo (1190 / 1360 / 1680) lo hace el firmware, asi que nunca sale un 1100.
  * Si un indice de eje o boton no existe en el mensaje, el eje cuenta como 0 y el
    boton como no presionado (o sea, sin hombre muerto no hay movimiento).

Los indices y los signos de los ejes son parametros (config/control_remoto.yaml):
confirmalos con scripts/ver_joy.py antes de manejar.
"""
import signal
import time

import rclpy
from rclpy.node import Node
from rclpy.signals import SignalHandlerOptions
from sensor_msgs.msg import Joy

from robocar.cierre import ignorar_senales_de_cierre, perro_guardian
from robocar_interfaces.msg import ComandoCarro

try:
    from rclpy.executors import ExternalShutdownException
except ImportError:  # pragma: no cover
    class ExternalShutdownException(Exception):
        pass


def recortar(x, minimo, maximo):
    return max(minimo, min(maximo, x))


def zona_muerta(x, zona):
    """Quita la zona muerta y reescala para que el recorrido siga llegando a +-1."""
    if abs(x) <= zona:
        return 0.0
    signo = 1.0 if x > 0 else -1.0
    return signo * recortar((abs(x) - zona) / (1.0 - zona), 0.0, 1.0)


def rampa(actual, objetivo, paso_acel, paso_freno):
    """Mueve 'actual' hacia 'objetivo' sin pasarse de paso_acel (acelerando) o paso_freno (frenando)."""
    if objetivo == actual:
        return actual
    acelerando = abs(objetivo) > abs(actual) and (objetivo * actual >= 0)
    paso = paso_acel if acelerando else paso_freno
    if objetivo > actual:
        return min(objetivo, actual + paso)
    return max(objetivo, actual - paso)


class TeleopXboxNode(Node):

    def __init__(self):
        super().__init__('teleop_xbox_node')

        # --- indices de /joy (confirmar con scripts/ver_joy.py)
        self.declare_parameter('eje_vel', 1)               # stick izquierdo, vertical
        self.declare_parameter('eje_dir', 2)               # stick derecho, horizontal
        self.declare_parameter('signo_vel', 1.0)           # +1: arriba da velocidad positiva
        self.declare_parameter('signo_dir', -1.0)          # -1: en ROS izquierda es +, y derecha = +100
        self.declare_parameter('boton_hombre_muerto', 9)   # LB
        self.declare_parameter('boton_turbo', 10)          # RB
        # --- ajustes de manejo
        self.declare_parameter('zona_muerta', 0.08)
        self.declare_parameter('vel_max', 30.0)            # % de velocidad hacia adelante
        self.declare_parameter('vel_max_turbo', 60.0)
        self.declare_parameter('vel_max_reversa', 20.0)
        self.declare_parameter('dir_max', 100.0)
        self.declare_parameter('rampa_acel', 10.0)         # % maximo que sube por ciclo
        self.declare_parameter('rampa_freno', 30.0)        # % maximo que baja por ciclo
        self.declare_parameter('timeout_joy', 0.5)         # s sin /joy -> parar de golpe
        self.declare_parameter('frecuencia', 20.0)         # Hz

        g = lambda n: self.get_parameter(n).value
        self.eje_vel = int(g('eje_vel'))
        self.eje_dir = int(g('eje_dir'))
        self.signo_vel = float(g('signo_vel'))
        self.signo_dir = float(g('signo_dir'))
        self.b_muerto = int(g('boton_hombre_muerto'))
        self.b_turbo = int(g('boton_turbo'))
        self.zona = recortar(float(g('zona_muerta')), 0.0, 0.9)
        self.vel_max = recortar(float(g('vel_max')), 0.0, 100.0)
        self.vel_max_turbo = recortar(float(g('vel_max_turbo')), 0.0, 100.0)
        self.vel_max_rev = recortar(float(g('vel_max_reversa')), 0.0, 100.0)
        self.dir_max = recortar(float(g('dir_max')), 0.0, 100.0)
        self.rampa_acel = max(1.0, float(g('rampa_acel')))
        self.rampa_freno = max(1.0, float(g('rampa_freno')))
        self.timeout_joy = float(g('timeout_joy'))
        frecuencia = max(5.0, float(g('frecuencia')))

        self._joy = None
        self._t_joy = 0.0
        self._vel = 0.0                 # velocidad que se esta mandando (con rampa)
        self._activo_prev = False
        self._periodo = 1.0 / frecuencia   # s entre ciclos del timer (el latido)
        self._t_rampa = time.monotonic()   # ultimo instante en que se avanzo la rampa
        self._ult_pub = None               # (vel, dir) del ultimo /carro/cmd publicado
        self._vivo_prev = None

        self.pub = self.create_publisher(ComandoCarro, '/carro/cmd', 10)
        self.create_subscription(Joy, '/joy', self._on_joy, 10)
        self.create_timer(1.0 / frecuencia, self._ciclo)

        self.get_logger().info(
            f'Teleop listo. Manten LB (boton {self.b_muerto}) para manejar; RB (boton {self.b_turbo}) = turbo. '
            f'vel_max {self.vel_max:.0f} %, turbo {self.vel_max_turbo:.0f} %, reversa {self.vel_max_rev:.0f} %.')

    # ------------------------------------------------------------------ /joy
    def _on_joy(self, msg):
        self._joy = msg
        self._t_joy = time.monotonic()
        # Reaccionar al llegar el /joy, sin esperar al siguiente tick del timer (ahorra hasta 50 ms).
        # El timer sigue publicando cada ciclo como latido.
        self._ciclo(por_evento=True)

    def _boton(self, i):
        j = self._joy
        return bool(j is not None and 0 <= i < len(j.buttons) and j.buttons[i])

    def _eje(self, i):
        j = self._joy
        if j is None or not (0 <= i < len(j.axes)):
            return 0.0
        return float(j.axes[i])

    # ----------------------------------------------------------------- ciclo
    def _ciclo(self, por_evento=False):
        ahora = time.monotonic()
        vivo = self._joy is not None and (ahora - self._t_joy) <= self.timeout_joy
        activo = vivo and self._boton(self.b_muerto)
        turbo = activo and self._boton(self.b_turbo)

        if vivo != self._vivo_prev:
            if not vivo and self._vivo_prev is not None:
                self.get_logger().warn('No llega /joy (control apagado o desconectado): freno y centro')
            elif vivo and self._vivo_prev is False:
                self.get_logger().info('Volvio /joy')
            self._vivo_prev = vivo
        if activo != self._activo_prev:
            self.get_logger().info('Hombre muerto presionado: manejo habilitado' if activo
                                   else 'Hombre muerto suelto: carro detenido')
            self._activo_prev = activo

        if not vivo:
            # sin senal del control: parar de golpe, sin rampa
            self._vel = 0.0
            objetivo_vel, objetivo_dir = 0.0, 0.0
        elif not activo:
            objetivo_vel, objetivo_dir = 0.0, 0.0
        else:
            v = zona_muerta(self._eje(self.eje_vel) * self.signo_vel, self.zona)
            if v >= 0:
                tope = self.vel_max_turbo if turbo else self.vel_max
            else:
                tope = self.vel_max_rev
            objetivo_vel = v * tope
            d = zona_muerta(self._eje(self.eje_dir) * self.signo_dir, self.zona)
            objetivo_dir = recortar(d * 100.0, -self.dir_max, self.dir_max)

        # La rampa se define por ciclo del timer (rampa_acel % cada 1/frecuencia s). Se escala con el tiempo
        # transcurrido para que correrla tambien por evento NO la acelere. Nunca mas de un paso completo.
        dt = ahora - self._t_rampa
        if por_evento and dt < 0.005:
            factor = 0.0                          # evento pegado a otro: no avanza la rampa
        else:
            factor = recortar(dt / self._periodo, 0.0, 1.0)
            self._t_rampa = ahora
        self._vel = rampa(self._vel, objetivo_vel, self.rampa_acel * factor, self.rampa_freno * factor)
        if por_evento:
            # por evento solo se publica si hay algo nuevo; si no, el timer ya manda el latido
            nuevo = (int(recortar(round(self._vel), -100, 100)), int(recortar(round(objetivo_dir), -100, 100)))
            if nuevo == self._ult_pub:
                return
        self._publicar(self._vel, objetivo_dir)

    def _publicar(self, vel, dir_):
        m = ComandoCarro()
        m.vel = int(recortar(round(vel), -100, 100))
        m.dir = int(recortar(round(dir_), -100, 100))
        self._ult_pub = (m.vel, m.dir)
        self.pub.publish(m)

    def parar(self):
        """Ultimo mensaje al cerrar: detenido y centrado (tres veces, por si se pierde uno)."""
        for _ in range(3):
            try:
                self._publicar(0.0, 0.0)
            except Exception:
                return
            time.sleep(0.02)


def _terminar(signum, frame):
    raise KeyboardInterrupt


def main(args=None):
    # Manejamos nosotros Ctrl+C y SIGTERM: si rclpy los maneja, invalida el contexto antes
    # de que podamos mandar el ultimo 0,0.
    rclpy.init(args=args, signal_handler_options=SignalHandlerOptions.NO)
    signal.signal(signal.SIGTERM, _terminar)
    nodo = TeleopXboxNode()
    try:
        rclpy.spin(nodo)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        ignorar_senales_de_cierre()      # ros2 launch manda SIGINT dos veces: la 2a no debe cortar el cierre
        perro_guardian(8.0)              # si el cierre se atorara, salir a la fuerza a los 8 s
        nodo.parar()
        nodo.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
