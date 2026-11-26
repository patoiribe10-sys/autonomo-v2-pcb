#pragma once
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <stdio.h>
#include <stdlib.h>
#define constrain(x,a,b) ((x)<(a)?(a):((x)>(b)?(b):(x)))
class Stream { public: virtual ~Stream() {} };
inline uint32_t millis() { return 0; }
