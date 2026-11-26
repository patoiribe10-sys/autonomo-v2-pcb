#!/usr/bin/env python3
"""Prueba segura del firmware carro-v2 desde la Jetson.

Uso:
    python3 prueba_serial.py                      # /dev/esp32, con motor
    python3 prueba_serial.py /dev/ttyUSB1
    python3 prueba_serial.py --solo-direccion     # no mueve el motor

IMPORTANTE: el puerto se abre con DTR/RTS apagados. Si no, el CH340 reinicia
al ESP32 cada vez que se abre. Ruedas al aire la primera vez.
"""
import argparse
import sys
import time

import serial

INTERVALO = 0.1   # mandamos un comando cada 100 ms (el timeout del ESP32 es 300 ms)


def abrir(puerto):
    ser = serial.Serial()
    ser.port = puerto
    ser.baudrate = 115200
    ser.timeout = 0.02
    ser.dsrdtr = False
    ser.rtscts = False
    ser.dtr = False      # antes de open(), para que no se active al abrir
    ser.rts = False
    ser.open()
    return ser


def leer(ser, t0):
    """Imprime todo lo que haya llegado del ESP32."""
    while ser.in_waiting:
        linea = ser.readline().decode(errors="replace").rstrip()
        if linea:
            print(f"  [{time.time() - t0:6.2f}s] <- {linea}")


def mantener(ser, t0, vel, dir_, segundos, texto):
    """Manda V<vel>,S<dir> cada 100 ms durante 'segundos'."""
    print(f"-> {texto}: V{vel},S{dir_} por {segundos} s")
    fin = time.time() + segundos
    while time.time() < fin:
        ser.write(f"V{vel},S{dir_}\n".encode())
        inicio = time.time()
        while time.time() - inicio < INTERVALO:
            leer(ser, t0)
            time.sleep(0.01)


def main():
    ap = argparse.ArgumentParser(description="Prueba serial del carro-v2")
    ap.add_argument("puerto", nargs="?", default="/dev/esp32")
    ap.add_argument("--solo-direccion", action="store_true", help="no mueve el motor")
    args = ap.parse_args()

    try:
        ser = abrir(args.puerto)
    except serial.SerialException as e:
        print(f"No pude abrir {args.puerto}: {e}")
        return 1

    t0 = time.time()
    try:
        time.sleep(0.5)
        ser.reset_input_buffer()

        print("-> P")
        ser.write(b"P\n")
        fin = time.time() + 0.5
        while time.time() < fin:
            leer(ser, t0)
            time.sleep(0.01)

        mantener(ser, t0, 0, 0, 1.5, "centro")
        mantener(ser, t0, 0, -100, 1.5, "izquierda")
        mantener(ser, t0, 0, 100, 1.5, "derecha")
        mantener(ser, t0, 0, 0, 1.5, "centro")

        if not args.solo_direccion:
            mantener(ser, t0, 25, 0, 2.0, "adelante lento")
            mantener(ser, t0, 0, 0, 1.0, "alto")

        print("Fin de la prueba. Dejo de mandar comandos (el ESP32 debe pasar a e=2).")
        fin = time.time() + 1.0
        while time.time() < fin:
            leer(ser, t0)
            time.sleep(0.01)
    except KeyboardInterrupt:
        print("\nInterrumpido.")
    finally:
        try:
            for _ in range(3):          # siempre dejar el carro en alto y centrado
                ser.write(b"V0,S0\n")
                time.sleep(0.05)
        except Exception:
            pass
        ser.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
