# Prueba en el host (Jetson o PC) de protocolo.cpp y direccion.cpp, SIN ESP32 ni PlatformIO.
# Usa unos stubs minimos de Arduino.h y ESP32Servo.h; no toca ningun archivo del firmware.
#   make        compila y corre
SRC = ../../src
INC = ../../include

test: test_host
	./test_host

test_host: test_host.cpp $(SRC)/protocolo.cpp $(SRC)/direccion.cpp
	g++ -std=c++17 -Wall -I stubs -I $(INC) test_host.cpp $(SRC)/protocolo.cpp $(SRC)/direccion.cpp -o test_host

clean:
	rm -f test_host telemetria.txt
