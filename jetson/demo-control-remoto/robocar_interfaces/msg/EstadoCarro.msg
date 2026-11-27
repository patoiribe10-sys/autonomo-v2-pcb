# Estado del carro, sacado de la telemetria del ESP32: v<pulsos/s>,s<dir>,b<mV>,e<estado>

# true si esta llegando telemetria del ESP32 (puerto abierto y datos frescos)
bool conectado

# Velocidad medida por el encoder, en pulsos por segundo (positiva hacia adelante)
int32 pulsos_s

# Direccion actual del servo, de -100 a 100
int8 dir

# Voltaje de la bateria en milivolts. 0 = el ESP32 solo tiene USB (no hay bateria), no es bateria critica.
uint16 bateria_mv

# Estado: 0 ok, 1 paro de emergencia, 2 timeout (no llegan comandos), 3 bateria baja o critica
uint8 estado

# Lo mismo en texto
string estado_texto

# Cuando llego la ultima telemetria
builtin_interfaces/Time ultima_telemetria
