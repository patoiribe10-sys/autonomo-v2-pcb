# Guía de usuario: puesta en marcha

Esta guía es para alguien del equipo que recibe la placa y necesita dejarla funcionando en el carro. Los pines exactos de cada conector están en [Pinout](../hardware/pinout.md).

> La placa todavía está en fabricación. Los pasos salen del diseño y del plan de pruebas; cuando se validen con la placa en la mano se van a corregir aquí mismo.

## Qué se necesita

- Batería LiPo 3S con conector XT60, cargada y balanceada.
- Interruptor de dos terminales, o un puente de cable para pruebas.
- Cable USB-C de datos.
- Cables con conector JST XH: motor y encoder (6 pines), servo (3), Jetson (4).
- Multímetro.
- Para la primera vez, de preferencia una fuente de laboratorio con límite de corriente.

## Antes de conectar la batería

1. Revisa a simple vista que no haya soldadura haciendo puente, sobre todo en los pines del USB-C (J1) y del puente H (U5).
2. Con el multímetro en continuidad, confirma que **no** haya corto entre cada riel y GND. Usa los test points TP7 (VBAT), TP8 (+5V), TP9 (+3V3), TP10 (+5V_SERVO) y TP11 (+VJET) contra TP12.
3. Verifica que el fusible F1 esté en su portafusible.

## Primer encendido

1. Pon un puente en **P2** (o conecta el interruptor) y otro entre los **pines 3 y 4 de J10**.
2. Si tienes fuente de laboratorio, ajústala a 11.1 V con límite de 150 a 200 mA y conéctala en P1 respetando el + y el − de la serigrafía. Sin nada conectado, la placa debe consumir mucho menos que eso.
3. Deben encender cuatro LEDs: **3V3, 5V, SRV y VJET**.
4. Mide los voltajes:

| Punto | Esperado |
|---|---|
| TP7 (VBAT) | Lo mismo que la fuente |
| TP8 (+5V) | Cerca de 4.9 V |
| TP9 (+3V3) | 3.3 V |
| TP10 (+5V_SERVO) | Cerca de 5.2 V |
| TP11 (+VJET) y J5 | 10 V |

Si un LED no enciende o un voltaje no coincide, desconecta y revisa ese regulador antes de seguir. Nunca conectes la Jetson sin haber medido los 10 V en J5.

## Conexión en el carro

Conecta en este orden, con la batería desconectada:

1. **Motor y encoder** en J2.
2. **Servo** en J3. Ojo con el orden: GND, 5 V, señal. Muchos servos traen el conector con la señal en otra orilla.
3. **Paro de emergencia** (normalmente cerrado) entre los pines 3 y 4 de J10, y el botón START externo entre 1 y 2 si se usa.
4. **Jetson:** el cable serial en J4 y la alimentación en J5 (pin 1 positivo).
5. **Interruptor** en P2.
6. Opcionales: luces en J9, buzzer en J8, tira LED en J7, sensores en J11 y J12.
7. Al final, la **batería** en P1.

## Uso normal

1. Cierra el interruptor. Encienden los cuatro LEDs de riel y el LED HB empieza a parpadear cuando el ESP32 arranca.
2. La Jetson enciende con los 10 V de J5 y tarda en cargar su sistema.
3. El botón **START** (S3 en la placa, o el externo) le indica al firmware que puede arrancar.
4. Para detener el carro de inmediato, oprime el **paro de emergencia**. El motor se queda sin energía; el servo, el ESP32 y la Jetson siguen encendidos.
5. Para apagar, abre el interruptor.

## Cuidados

- **Batería baja.** Por debajo de unos 10.5 V el regulador de la Jetson ya no alcanza los 10 V y la Jetson puede reiniciarse. Recarga antes de llegar ahí.
- **Luces.** J9 entrega voltaje de batería, no 5 V. Usa luces de 12 V o pon una resistencia.
- **I2C y J14** trabajan a 3.3 V. No conectes señales de 5 V.
- **USB y batería a la vez** se pueden usar sin problema; los diodos D1 y D2 separan las dos fuentes.
- **Fusible.** Si la placa no enciende y la batería está bien, revisa F1 y el puente o interruptor de P2.

## Si algo no funciona

| Síntoma | Qué revisar |
|---|---|
| No enciende ningún LED | Interruptor o puente en P2, fusible F1, polaridad de la batería |
| Encienden los LEDs pero el motor no gira | Lazo del paro en J10 (pines 3 y 4), pin STBY en TP1 (debe estar en 3.3 V) |
| El ESP32 se reinicia al abrir el puerto serial | Es normal con los puentes de JP1 puestos. Quítalos si molesta |
| La computadora no ve el puerto | Cable USB sin datos, o falta el driver del CH340 |
| La Jetson se reinicia en movimiento | Batería baja |
| La Jetson no recibe datos | TX y RX cruzados en el cable de J4; mide TP5 (debe estar en 3.3 V en reposo) |
