"""control_remoto_launch.py: manejar con el control de Xbox y ver las camaras en el navegador.

Arranca:
  game_controller_node  -> /joy (del control Bluetooth)
  teleop_xbox_node      -> /carro/cmd (hombre muerto en LB)
  serial_bridge_node    -> habla con el ESP32 por /dev/esp32 y publica /carro/estado
  camaras_node          -> http://<ip de la Jetson>:8080

Todos los parametros estan en config/control_remoto.yaml.

Si existe config/sdl_gamecontroller.txt (una linea de SDL_GAMECONTROLLERCONFIG), se la pasa SOLO a
game_controller_node. Sirve para este control BLE (045e:0b13), cuyo mapeo de fabrica en SDL
no coincide con los codigos que da el kernel 5.15 de la Jetson. Ver scripts/calibrar_control.py.

Argumentos (todos opcionales; sirven para simular o probar por partes):
    puerto:=<ruta>      puerto serial del puente (por defecto el del yaml: /dev/esp32). Con otro valor NO se
                        usa el respaldo /dev/ttyUSB0. Ej.: un pseudo-terminal con un ESP32 falso.
    joy:=false          no arranca game_controller_node (para inyectar un /joy falso)
    camaras:=false      no arranca camaras_node

    ros2 launch robocar control_remoto_launch.py
    ros2 launch robocar control_remoto_launch.py puerto:=/tmp/esp32_sim joy:=false camaras:=false
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def _nodos(context, *args, **kwargs):
    compartido = get_package_share_directory('robocar')
    config = os.path.join(compartido, 'config', 'control_remoto.yaml')

    puerto = LaunchConfiguration('puerto').perform(context).strip()
    con_joy = LaunchConfiguration('joy').perform(context).strip().lower() != 'false'
    con_camaras = LaunchConfiguration('camaras').perform(context).strip().lower() != 'false'

    env_control = {}
    sdl = os.path.join(compartido, 'config', 'sdl_gamecontroller.txt')
    if os.path.exists(sdl):
        with open(sdl) as f:
            env_control['SDL_GAMECONTROLLERCONFIG'] = f.read().strip()

    params_puente = [config]
    if puerto:
        params_puente.append({'puerto': puerto, 'puerto_respaldo': '/dev/no_existe'})

    nodos = []
    if con_joy:
        nodos.append(Node(package='joy', executable='game_controller_node', name='game_controller_node',
                          parameters=[config], additional_env=env_control, output='screen'))
    nodos.append(Node(package='robocar', executable='teleop_xbox_node', name='teleop_xbox_node',
                      parameters=[config], output='screen'))
    nodos.append(Node(package='robocar', executable='serial_bridge_node', name='serial_bridge_node',
                      parameters=params_puente, output='screen'))
    if con_camaras:
        nodos.append(Node(package='robocar', executable='camaras_node', name='camaras_node',
                          parameters=[config], output='screen'))
    return nodos


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('puerto', default_value='',
                              description='puerto serial del puente (vacio = el del yaml)'),
        DeclareLaunchArgument('joy', default_value='true', description='false = sin game_controller_node'),
        DeclareLaunchArgument('camaras', default_value='true', description='false = sin camaras_node'),
        OpaqueFunction(function=_nodos),
    ])
