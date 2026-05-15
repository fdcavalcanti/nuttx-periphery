"""Tests for NuttX ioctl constants."""

from nuttx_periphery import ioctl_consts as c


def test_ioctl_base_values() -> None:
    assert c.PWMIOC_BASE == 0x0C00
    assert c.ULED_BASE == 0x1D00
    assert c.I2C_BASE == 0x2100
    assert c.SPI_BASE == 0x2200
    assert c.GPIO_BASE == 0x2300


def test_gpio_ioctl_values() -> None:
    assert c.GPIOC_WRITE == 0x2301
    assert c.GPIOC_READ == 0x2302
    assert c.GPIOC_PINTYPE == 0x2303
    assert c.GPIOC_REGISTER == 0x2304
    assert c.GPIOC_UNREGISTER == 0x2305
    assert c.GPIOC_SETPINTYPE == 0x2306
    assert c.GPIOC_SETDEBOUNCE == 0x2307
    assert c.GPIOC_IRQ_SETMASK == 0x2308


def test_pwm_ioctl_values() -> None:
    assert c.PWMIOC_SETCHARACTERISTICS == 0x0C01
    assert c.PWMIOC_GETCHARACTERISTICS == 0x0C02
    assert c.PWMIOC_START == 0x0C03
    assert c.PWMIOC_STOP == 0x0C04
    assert c.PWMIOC_FAULTS_FETCH_AND_CLEAR == 0x0C05


def test_userled_ioctl_values() -> None:
    assert c.ULEDIOC_SUPPORTED == 0x1D01
    assert c.ULEDIOC_SETLED == 0x1D02
    assert c.ULEDIOC_SETALL == 0x1D03
    assert c.ULEDIOC_GETALL == 0x1D04
    assert c.ULEDIOC_SUPEFFECT == 0x1D05
    assert c.ULEDIOC_SETEFFECT == 0x1D06


def test_i2c_and_spi_ioctl_values() -> None:
    assert c.I2CIOC_TRANSFER == 0x2101
    assert c.I2CIOC_RESET == 0x2102
    assert c.SPIIOC_TRANSFER == 0x2201
