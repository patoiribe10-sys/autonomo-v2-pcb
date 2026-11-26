# Prueba en el host del protocolo y del servo

Compila y ejecuta `protocolo.cpp` y `direccion.cpp` del firmware `carro-v2` como un programa normal (no en el ESP32),
con stubs mínimos de `Arduino.h` y `ESP32Servo.h`. No cambia ningún archivo del firmware.

```
cd firmware/carro-v2/tools/test_host
make
```

Comprueba (32 casos): `S=+100` da 1730 µs (derecha), `S=-100` da 1190 µs y el servo nunca sale de 1190–1730;
las líneas malformadas (`V5.5,S0`, `V30`, `v30,s10`, `V30,S10x`, etc.) se ignoran sin tocar el comando anterior;
y que `protocolo_telemetria()` cabe en 48 bytes y no devuelve una línea cortada. También escribe `telemetria.txt`
con 240 líneas de telemetría para comprobar que el regex del puente de la Jetson las entiende.
