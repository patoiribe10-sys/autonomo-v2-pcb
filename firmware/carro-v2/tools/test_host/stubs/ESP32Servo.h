#pragma once
class Servo { public: int ultimo_us = -1; void attach(int, int = 0, int = 0) {} void writeMicroseconds(int us) { ultimo_us = us; } void setPeriodHertz(int) {} };
namespace ESP32PWM { inline void allocateTimer(int) {} }
