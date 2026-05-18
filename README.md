# nuttx-periphery

Pure Python peripheral APIs for NuttX character devices.

Current status:
- GPIO support implemented first
- User LED control support implemented
- PWM control support implemented
- ioctl constants included for GPIO, PWM, UserLED
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

For future peripheral modules:
- PWM: `CONFIG_PWM`
- User LED: `CONFIG_USERLED`

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

