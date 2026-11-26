// Constantes ajustables del firmware del carro. Todo lo que se toca va aqui.
#pragma once
#include <stdint.h>

// ---------- Comunicacion ----------
#define BAUDIOS            115200
#define LINEA_MAX          32      // tamano maximo de una linea recibida (con \n)
#define TELEMETRIA_MS      50      // 20 Hz
#define TIMEOUT_CMD_MS     300     // sin comando valido en este tiempo -> frena y centra

// ---------- Motor ----------
#define DIR_ADELANTE       1       // 1 o -1 segun hacia donde gire el motor (igual que el demo)
#define MOTOR_PWM_HZ       20000
#define MOTOR_PWM_BITS     8
#define PWM_MAX            255
#define PWM_MIN_ARRANQUE   60      // zona muerta: con |vel| > 0 nunca bajamos de esto
#define RAMPA_PWM_PASO     8       // cuanto cambia el PWM por paso de rampa
#define RAMPA_PASO_MS      10      // cada cuanto se da un paso (8/10 ms = 0 a 255 en ~0.3 s)

// ---------- Direccion (servo) ----------
#define SERVO_VEL_US_S     1500.0f // velocidad maxima del servo en us por segundo

// ---------- Encoder ----------
#define ENC_VENTANA_MS     50      // cada cuanto se calculan los pulsos/s
#define ENC_SIGNO         -1       // probado 25-nov: con la ISR de prueba-pcb adelante contaba negativo. -1 lo deja positivo

// ---------- Paro de emergencia (ADC en GPIO 39) ----------
#define ESTOP_UMBRAL_V     5.0f    // voltaje calculado arriba de esto = paro ACTIVO
#define ESTOP_MUESTREO_MS  10
#define ESTOP_CONF_ON      2       // lecturas seguidas para activar (~20 ms)
#define ESTOP_CONF_OFF     5       // lecturas seguidas para liberar (~50 ms)

// ---------- Bateria (ADC en GPIO 36) ----------
#define BAT_MUESTREO_MS    10
#define BAT_N_MUESTRAS     32      // promedio movil (~320 ms)
#define BAT_SIN_BATERIA_MV 3000    // abajo de esto se asume que solo hay USB
#define BAT_BAJA_MV        10500   // abajo de esto (por BAT_BAJA_T_MS) -> pitido y vel max 50%
#define BAT_BAJA_T_MS      2000
#define BAT_CRITICA_MV     9900    // abajo de esto (por BAT_CRITICA_T_MS) -> motor apagado
#define BAT_CRITICA_T_MS   1000    // evita que un bajon por arranque del motor apague todo
#define BAT_RECUPERA_MV    10800   // histeresis: arriba de esto se quita la alarma
#define BAT_VEL_MAX_BAJA   50      // % de velocidad maxima con bateria baja
#define BUZZER_ON_MS       200
#define BUZZER_OFF_MS      800

// ---------- Botones ----------
#define PIN_BOOT           0       // boton BOOT (S2), LOW = presionado
#define BOTON_REBOTE_MS    30

// ---------- LED HB ----------
#define LED_OK_MS          500     // 1 Hz
#define LED_FALLA_MS       100     // rapido

// ---------- Estados que se reportan (campo e) ----------
#define ESTADO_OK          0
#define ESTADO_PARO        1
#define ESTADO_TIMEOUT     2
#define ESTADO_BAT_BAJA    3
