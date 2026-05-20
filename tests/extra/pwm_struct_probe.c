#include <stdint.h>
#include <stdio.h>
#include <string.h>

#ifndef POINTER_SIZE
#define POINTER_SIZE 8
#endif

#ifndef CHANNEL_COUNT
#define CHANNEL_COUNT 2
#endif

typedef uint32_t ub16_t;

#if POINTER_SIZE == 4
typedef uint32_t ptr_t;
#elif POINTER_SIZE == 8
typedef uint64_t ptr_t;
#else
#error "POINTER_SIZE must be 4 or 8"
#endif

struct pwm_chan_s
{
  ub16_t duty;
#ifdef HAS_DEADTIME
  ub16_t dead_time_a;
  ub16_t dead_time_b;
#endif
  uint8_t cpol;
  uint8_t dcpol;
  int8_t channel;
#ifdef HAS_PULSECOUNT
  uint32_t count;
#endif
};

struct pwm_info_s
{
  uint32_t frequency;
  struct pwm_chan_s channels[CHANNEL_COUNT];
  ptr_t arg;
};

int main(void)
{
  struct pwm_info_s info;
  memset(&info, 0, sizeof(info));

  info.frequency = 20000;

  info.channels[0].duty = 1000;
  info.channels[0].cpol = 1;
  info.channels[0].dcpol = 2;
  info.channels[0].channel = 0;
#ifdef HAS_DEADTIME
  info.channels[0].dead_time_a = 11;
  info.channels[0].dead_time_b = 12;
#endif
#ifdef HAS_PULSECOUNT
  info.channels[0].count = 33;
#endif

#if CHANNEL_COUNT > 1
  info.channels[1].duty = 2000;
  info.channels[1].cpol = 0;
  info.channels[1].dcpol = 1;
  info.channels[1].channel = -1;
#ifdef HAS_DEADTIME
  info.channels[1].dead_time_a = 21;
  info.channels[1].dead_time_b = 22;
#endif
#ifdef HAS_PULSECOUNT
  info.channels[1].count = 44;
#endif
#endif

#if POINTER_SIZE == 8
  info.arg = 0x1122334455667788ULL;
#else
  info.arg = 0x55667788UL;
#endif

  (void)fwrite(&info, 1, sizeof(info), stdout);
  return 0;
}
