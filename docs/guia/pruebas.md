# Firmware y plan de pruebas

- [main.cpp](../../firmware/prueba-pcb/src/main.cpp)
- [platformio.ini](../../firmware/prueba-pcb/platformio.ini)

Para validar la placa hay un firmware aparte del que usa el carro. Prueba cada bloque por separado desde un menú en el monitor serial, de modo que una falla se pueda ubicar sin adivinar.

## Firmware de prueba

Está en [`firmware/prueba-pcb/`](https://github.com/patoiribe10-sys/autonomo-v2-pcb/tree/main/firmware/prueba-pcb). Se abre con PlatformIO, se carga y se usa a 115200 baudios. Se escribe la opción y cualquier tecla cancela la prueba en curso.

| Opción | Prueba | Qué se debe ver |
|---|---|---|
| 1 | LED HB | Diez parpadeos de D5 |
| 2 | Voltajes | VBAT y estado del paro; se compara con el multímetro |
| 3 | START y paro | Mensajes al presionar START y al abrir o cerrar el lazo |
| 4 | Motor y encoder | Rampa hacia adelante y hacia atrás, con el conteo del encoder |
| 5 | Encoder a mano | Pulsos al girar la llanta |
| 6 | Servo | Centro, izquierda, centro, derecha (1360, 1100 y 1730 µs) |
| 7 | Buzzer | Tres pitidos |
| 8 | Luces | Tres encendidos de un segundo |
| 9 | Tira LED | Rojo, verde, azul y blanco |
| a | UART de la Jetson | Manda PING cada segundo. Con un puente entre los pines 2 y 3 de J4 debe regresar lo mismo |
| b | I2C | Direcciones de los dispositivos conectados |
| c | GPIO extra | IO4 e IO5 alternan cada medio segundo |
| d | Línea HB | Cambios de nivel en el pin 4 de J4 |

> La prueba 4 se hace con las llantas en el aire y con el puente entre los pines 3 y 4 de J10.

## Plan de pruebas al recibir la placa

| # | Etapa | Criterio para pasar |
|---|---|---|
| 1 | Revisión visual | Sin puentes de soldadura en J1 ni en U5; polaridades correctas |
| 2 | Resistencia de cada riel a GND | Ningún riel en corto |
| 3 | Encendido con fuente limitada a 11.1 V y 150–200 mA | +5V ≈ 4.9 V, +3V3 = 3.3 V, +VJET ≈ 10 V, +5V_SERVO ≈ 5.2 V |
| 4 | USB | La computadora reconoce el puerto y carga firmware |
| 5 | Firmware de prueba | Opciones 1, 2 y 3 correctas |
| 6 | Motor, encoder y paro | El motor gira en los dos sentidos y se detiene solo al abrir el lazo, aunque haya PWM |
| 7 | Servo | Recorre el rango sin que caigan los 5 V de lógica |
| 8 | Jetson | Enciende con J5 y hay comunicación por J4 |
| 9 | Resto de conectores | Buzzer, luces, tira LED, I2C y GPIO |
| 10 | Térmica y rizado | Reguladores a temperatura razonable con carga; rizado medido con osciloscopio |

Hay dos mediciones que importan más que las otras porque eran las fallas de la versión anterior:

- **STBY** (TP1) debe estar en 3.3 V.
- **TX hacia la Jetson** (TP5) debe estar en alto en reposo.

Los resultados se van a publicar en [Resultado final](../resultado.md).
