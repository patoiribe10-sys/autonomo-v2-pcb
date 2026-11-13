# Preguntas frecuentes

## ¿Por qué se rehízo la placa?

La v1 funcionaba con parches: un puente para el pin STBY, el serial con la Jetson por USB porque el UART de la placa no servía, y reinicios cada vez que el servo pedía corriente. Con el cambio a Altium se aprovechó para corregir todo eso e integrar los módulos sueltos.

## ¿Por qué cuatro capas si la v1 era de dos?

Por el plano de GND continuo y por espacio. Tres reguladores conmutados en una placa de 10 × 10 cm necesitan retornos cortos, y con dos capas las pistas de potencia y las de señal se cruzaban demasiado. El costo adicional en un prototipo es pequeño.

## ¿Se puede usar sin la Jetson?

Sí. El ESP32 funciona solo; J5 y J4 simplemente quedan libres. Así se hacen las pruebas de la placa en banco.

## ¿Puedo alimentar la placa solo con el USB?

Para programar y ver el monitor serial, sí. El motor, el servo y la Jetson necesitan la batería.

## ¿Qué pasa si conecto la batería al revés?

No enciende y no se daña: el MOSFET Q7 queda abierto.

## ¿El paro de emergencia depende del firmware?

No. Abre un MOSFET en la alimentación del motor. Funciona aunque el ESP32 esté trabado.

## ¿Por qué el paro no apaga también el servo?

Para conservar la dirección mientras el carro se detiene y no perder el estado de la Jetson. Si en las pruebas resulta mejor cortarlo todo, es un cambio para la siguiente versión.

## ¿Qué motor y qué servo usa?

Motor GM25-370 con encoder de cuadratura y servo MG995. El puente H admite otros motores de corriente continua mientras no pasen de unos 2 A continuos.

## ¿Por qué máscara negra?

Por gusto, y tuvo un costo: entre los pines del USB-C no queda puente de máscara. Está explicado en [Diseño de la PCB](hardware/pcb.md).

## ¿Dónde está el firmware del carro?

Este repositorio documenta solo la placa e incluye su firmware de prueba. El firmware de conducción y los nodos de ROS 2 son parte del proyecto completo del carro.

## ¿Puedo fabricar una igual?

Los Gerbers, el BOM y el archivo de posiciones están en [Archivos de diseño](hardware/archivos.md). Con eso un fabricante puede producirla y ensamblarla. El proyecto tiene licencia CC BY 4.0: se puede usar y modificar dando crédito al autor.
