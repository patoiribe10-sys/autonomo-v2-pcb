from setuptools import find_packages, setup
import os
from glob import glob

package_name = 'robocar'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'),
            glob('launch/*.py')),
        (os.path.join('share', package_name, 'config'),
            glob('config/*.yaml') + glob('config/*.txt')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='RoboUAQ',
    maintainer_email='patoiribe10-sys@users.noreply.github.com',
    description='RoboUAQ 2026 — Carro autónomo urbano 1:10',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'teleop_xbox_node = robocar.teleop_xbox_node:main',
            'serial_bridge_node = robocar.serial_bridge_node:main',
            'camaras_node = robocar.camaras_node:main',
            'lane_node = robocar.lane_node:main',
            'detect_node = robocar.detect_node:main',
            'nav_node = robocar.nav_node:main',
        ],
    },
)
