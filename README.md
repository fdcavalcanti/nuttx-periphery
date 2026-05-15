# nuttx-periphery

Pure Python peripheral APIs for NuttX character devices.

Current status:
- GPIO support implemented first
- User LED control support implemented
- ioctl constants included for GPIO, PWM, UserLED, I2C, and SPI
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

## NuttX Requirements

For GPIO:
- `CONFIG_DEV_GPIO=y`
- one or more GPIO character devices under `/dev` (e.g. `/dev/gpio0`)

For future peripheral modules:
- PWM: `CONFIG_PWM`
- I2C: `CONFIG_I2C_DRIVER`
- SPI: `CONFIG_SPI_DRIVER`
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

