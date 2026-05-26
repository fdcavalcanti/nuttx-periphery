# nuttx-periphery

Pure Python peripheral APIs for NuttX character devices.

Current status:
- GPIO support (including signal-based interrupt registration)
- User LED control support
- PWM control support
- Timer character devices (status, timeouts, signal notification)
- `struct sigevent` / `struct timer_notify_s` packing via ctypes
- ioctl constants for GPIO, PWM, UserLED, Timer, and signal notify modes
- no custom exception classes

## Scope

This package targets CPython running on NuttX and uses:
- `os.open` / `os.close`
- `fcntl.ioctl`

It follows a NuttX-first design with typed Python methods and a raw ioctl escape hatch.

## GPIO Example

```python
from nuttx_periphery import GPIO, GPIOPinType

with GPIO("/dev/gpio0") as gpio:
    gpio.set_pin_type(GPIOPinType.GPIO_OUTPUT_PIN)
    gpio.write(True)
```

## User LED Example

```python
from nuttx_periphery import UserLED

with UserLED("/dev/userleds") as leds:
    print(f"supported mask: 0x{leds.supported():08x}")
    leds.set_led(0, True)
    leds.set_all(0b101)
    print(f"current state: 0x{leds.get_all():08x}")
```

## PWM Example

```python
from nuttx_periphery import PWM, PWMInfo

with PWM("/dev/pwm0") as pwm:
    pwm.set_characteristics(PWMInfo(frequency=1_000, duty=32768))
    info = pwm.get_characteristics()
    print(info)
    pwm.start()
    pwm.stop()
```

Optional helper for pre-filled info:

```python
from nuttx_periphery import PWM

with PWM("/dev/pwm0", has_deadtime=True, has_pulsecount=True) as pwm:
    info = pwm.new_pwm_info(frequency=1_000, duty=32768)
    pwm.set_characteristics(info)
```

## Signal events (`struct sigevent`)

The `nuttx_periphery.sigevent` module mirrors NuttX `struct sigevent` from
`include/signal.h` (without `CONFIG_SIG_EVTHREAD`). Layout is built with
ctypes:

- `SigvalStruct` — `union sigval` (`sival_int` / `sival_ptr`)
- `SigeventStruct` — C layout used for ioctl buffers
- `Sigevent` — dataclass with `to_bytes()` / `from_bytes()`

NuttX signal numbers must be in the range **1–63** (`MAX_SIGNO`). Use
`SIGEV_SIGNAL` (from `ioctl_consts`) for normal signal delivery.

```python
from nuttx_periphery.ioctl_consts import SIGEV_SIGNAL
from nuttx_periphery.sigevent import Sigevent

# thread_id defaults to os.getpid()
notify = Sigevent.signal(signo=10, value=0)
payload = notify.to_bytes()  # bytes for GPIOC_REGISTER, etc.
```

`Sigevent` fields map to the C struct as follows:

| Python field | C field |
|--------------|---------|
| `notify` | `sigev_notify` |
| `signo` | `sigev_signo` |
| `value` | `sigev_value.sival_int` |
| `thread_id` | `_sigev_un._tid` |

## GPIO interrupt example

Register a signal when the pin interrupts (see `examples/gpio_interrupt.py`):

```python
import signal

from nuttx_periphery import GPIO, GPIOPinType
from nuttx_periphery.sigevent import Sigevent

signo = signal.SIGUSR1
signal.signal(signo, lambda s, f: print("GPIO interrupt"))

with GPIO("/dev/gpio0") as gpio:
    gpio.set_pin_type(GPIOPinType.GPIO_INTERRUPT_RISING_PIN)
    gpio.register_signal(Sigevent.signal(signo))
    # wait for the signal, then gpio.unregister_signal()
```

## Timer example

Poll timer status or wait for expiration via a signal:

```python
import signal
import time

from nuttx_periphery import Timer

signo = signal.SIGUSR1
signal.signal(signo, lambda s, f: print("timer expired"))

with Timer("/dev/timer0") as tmr:
    tmr.set_notification(signo, periodic=False)
    tmr.set_timeout_us(2_000_000)
    tmr.start()

    while tmr.is_active():
        status = tmr.get_status_us()
        print("time left (us):", status.timeleft)
        time.sleep(0.1)

    tmr.stop()
```

Lower-level access:

```python
from nuttx_periphery.timer import Timer, TimerNotify, pack_timer_notify

# Equivalent buffer for TCIOC_NOTIFICATION
buf = pack_timer_notify(10, pid=42, periodic=True)

notify = TimerNotify.signal(10, pid=42, periodic=True)
assert notify.to_bytes() == buf
```

`TimerStatus` exposes `active` and `has_handler` from the status flags.
Use `get_status_us()` / `get_status_ticks()` for time values in microseconds
or ticks; `read_status(cmd)` accepts a specific `TCIOC_*_GETSTATUS` ioctl.

## Generic read example

```python
from nuttx_periphery.device import CharacterDevice

buf = bytearray(32)

with CharacterDevice("/dev/random") as dev:
    nread = dev.read(buf, len(buf))

print("bytes read:", nread)
print("data:", bytes(buf[:nread]))
```

## NuttX Requirements

For GPIO:
- `CONFIG_DEV_GPIO=y`
- one or more GPIO character devices under `/dev` (e.g. `/dev/gpio0`)

For PWM:
- `CONFIG_PWM`

For User LED:
- `CONFIG_USERLED`

For Timer:
- timer character device under `/dev` (e.g. `/dev/timer0`)
- Python `signal` module to handle expiration notifications

## Development

Install dev dependencies:

```bash
python -m pip install -e ".[dev]"
```

Run tests:

```bash
pytest
```

## Build wheel

From the project root:

```bash
python -m pip install --upgrade build
python -m build --wheel
```

The generated `.whl` file will be in `dist/`.
