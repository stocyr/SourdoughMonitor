# Notes

## 04.09.2022 -- *Basic installation*

Code for scanning i2c devices connected:

```python
import board
import busio as io

i2c = io.I2C(board.SCL, board.SDA)
while not i2c.try_lock():
    pass
print([hex(x) for x in i2c.scan()])
```

We see the following devices connected:

- `0x0b`: LC709203
- `0x41`: TMF8821
- `0x77`: BME280
- `0x3c`: Zio ILED

To initialize the OLED display and show the REPL output as well as our own prints, run:

```python
import board
import displayio
import adafruit_ssd1327

displayio.release_displays()

i2c = board.I2C()

display_bus = displayio.I2CDisplay(i2c, device_address=0x3C)
display = adafruit_ssd1327.SSD1327(display_bus, width=128, height=128)
```

To use the buzzer, we need to connect it to a pin which supports PWM.
From [here](https://github.com/Dlloydev/ESP32-ESP32S2-AnalogWrite) we get a list of supported pins:

| Board    | PWM Pins                          | PWM Frequency   | Resolution                  |
| -------- | --------------------------------- | --------------- | --------------------------- |
| ESP32    | 2, 4, 5, 12-19, 21-23, 27, 32, 33 | 1000 Hz default | 1-16 bit PWM, 8-bit default |
| ESP32-S2 | 1- 14, 21, 33-42, 45              | 1000 Hz default | 1-16 bit PWM, 8-bit default |
| ESP32-C3 | 0- 9, 18, 19                      | 1000 Hz default | 1-16 bit PWM, 8-bit default |

We decide for pin `A5` (GPIO8).

To control the e-ink display, run:

```python
import time
import busio
import board
import displayio
import adafruit_il0373

displayio.release_displays()

# This pinout works on a Feather M4 and may need to be altered for other boards.
spi = busio.SPI(board.SCK, board.MOSI)  # Uses SCK and MOSI
epd_cs = board.D9
epd_dc = board.D10

display_bus = displayio.FourWire(
    spi, command=epd_dc, chip_select=epd_cs, baudrate=1000000
)
time.sleep(1)

display = adafruit_il0373.IL0373(display_bus, width=296, height=128, rotation=270, black_bits_inverted=False,
                                 color_bits_inverted=False, grayscale=True, refresh_time=1)
g = displayio.Group()

with open("/sketch.bmp", "rb") as f:
    pic = displayio.OnDiskBitmap(f)
    t = displayio.TileGrid(pic, pixel_shader=pic.pixel_shader)
    g.append(t)
    display.show(g)
    display.refresh()
    print("refreshed")
    time.sleep(120)
```

## 16.09.2022 -- *Peripheral Tests*

AM2320 answers correctly, but the example is wrong: reading consecutively with no sleep time in between doesn't work.
Thus, wait > 100ms between reading (even temperature --> humidity):

```python
import time
import board
from busio import I2C
import adafruit_am2320

# create the I2C shared bus
i2c = I2C(board.SCL, board.SDA, frequency=125000)
am = adafruit_am2320.AM2320(i2c)

delay = 0.1

while True:
    # Note: reading from the sensor within intervals of > 10Hz is not supported:
    # It goes to sleep mode and doesn't wake up on time. Thus, wait at least 100ms
    # before performing another reading. The sensor itself doesn't update the internal
    # measurement register more frequently than every 2s anyway.
    print("Temperature: ", am.temperature)
    time.sleep(delay)
    print("Humidity: ", am.relative_humidity)
    time.sleep(delay)
```
