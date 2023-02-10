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

## 02.10.2022 -- *BME280*

```python
"""
BME280
"""
import time
import board
import adafruit_bme280.advanced as adafruit_bme280

i2c = board.I2C()
bme280 = adafruit_bme280.Adafruit_BME280_I2C(i2c)

bme280.mode = adafruit_bme280.MODE_FORCE
bme280.iir_filter = adafruit_bme280.IIR_FILTER_DISABLE
bme280.overscan_temperature = adafruit_bme280.OVERSCAN_X16

while True:
    print(f'Temperature: {bme280.temperature:.2f}°')
    time.sleep(0.5)
```

We also found out we have the [revision C board](https://learn.adafruit.com/assets/109937),
since the open-state value of I2C_POWER is *low*

## 05.01.2023 -- *Bootup time*

We set the alarm time to `t_start + 15`
Time measured that the boot process takes until it gets to the `t_start = time.monotonic()`:
16.30, 16.27, 16.38, 16.21, 16.33
--> average: 16.298 ~ 16.3 ==> bootup time = 1.3s

## 06.01.2023 -- *AM2320 Connection Failures*

The AM2320 doesn't answer to I2C calls from a cold start of the uC. Soft restart makes it work flawlessly. Related
problems online:

- https://community.home-assistant.io/t/temperature-humidity-sensor-with-am2320-esp32/360126/10
- https://github.com/esphome/issues/issues/1742
- https://github.com/esphome/issues/issues/192#issuecomment-481171704

The following code works both in soft restarts and cold starts:

```python
import time
import board
from busio import I2C
import adafruit_am2320
import digitalio

led = digitalio.DigitalInOut(board.LED)
led.switch_to_output(True)

# Block 1: restart i2c bus
i2c_pow = digitalio.DigitalInOut(board.I2C_POWER)
i2c_pow.switch_to_input()
time.sleep(0.5)
default_state = i2c_pow.value
i2c_pow.switch_to_output(not default_state)
# Block 2: sleep before i2c initialization
time.sleep(2)
i2c = I2C(board.SCL, board.SDA, frequency=125000)
# Block 3: sleep between i2c initialization and sensor setup
time.sleep(2)
am = adafruit_am2320.AM2320(i2c)
# Block 4: sleep before sensor read
time.sleep(2)

delay = 0.3
while True:
    print("Temperature: ", am.temperature)
    time.sleep(delay)
    print("Humidity: ", am.relative_humidity)
    time.sleep(delay)
    led.value = not led.value
```

1. Trial: disable block 4 --> still works
2. Trial: disable blocks 3, 4 --> still works
3. Trial: disable blocks 2, 3, 4 --> fails
4. Trial: disable blocks 1, 3, 4 --> still works
5. Trial: disable blocks 1, 3, 4 and insert a i2c power-cycle between the 2s sleep and the i2c initialization --> fails
6. Trial: take trial 5 and move the 2s sleep between i2c power-cycle and i2c initialization --> works

It turns out the following code works in both cases:

```python
import time
import board
from busio import I2C
import adafruit_am2320
import digitalio

led = digitalio.DigitalInOut(board.LED)
led.switch_to_output(True)

time.sleep(2)
i2c = I2C(board.SCL, board.SDA, frequency=125000)
am = adafruit_am2320.AM2320(i2c)

delay = 0.3
while True:
    print("Temperature: ", am.temperature)
    time.sleep(delay)
    print("Humidity: ", am.relative_humidity)
    time.sleep(delay)
    led.value = not led.value
```

## 06.01.2023 -- *Timing profiling*

From the output of the code in state #6ae7d30, the following timings were extracted (using a soft reboot):

    sequence begin: 4.38, delta: 3.08
    -> after displayio.release_displays(): 4.38, delta: 0.00
    Wakeup: Reset
    -> after wakeup determination: 4.39, delta: 0.01
    -> after memory setup and read (ints): 4.40, delta: 0.01
    Buffers: 0, 5
    IO and memory initialized.
    Wake time until i2c init: 4.4s
    -> after i2c init: 4.40, delta: 0.01
    -> after board temp read: 4.72, delta: 0.32
    -> after temp value append: 4.72, delta: 0.00
    BME280 read.
    -> after ext temp read: 5.21, delta: 0.49
    AM2320 read.
    Distance: 11.00 with std = 0.0
    Floor height not calibrated yet
    -> after distance read: 7.00, delta: 1.79
    -> after battery read: 7.01, delta: 0.01
    battery monitor initialized.
    -> after display init: 7.12, delta: 0.11
    display initialized.
    -> after font load: 7.50, delta: 0.38
    Startup time just before checking the buttons: 6.20s
    -> after button handling: 7.51, delta: 0.00
    -> after background draw: 7.51, delta: 0.01
    Display background drawn.
    -> after text draw: 9.82, delta: 2.31
    Labels drawn.
    -> after battery draw: 9.84, delta: 0.02
    Battery symbol drawn.
    -> after growth write: 9.84, delta: 0.00
    -> after plot init: 9.85, delta: 0.01
    -> after full buffer read: 9.85, delta: 0.00
    -> after graph draw: 9.86, delta: 0.00
    -> after message text writes: 11.78, delta: 1.92
    Plot drawn.
    -> after display refresh: 12.60, delta: 0.82
    Display refreshed.
    -> after 2nd display_release(): 12.60, delta: 0.00
    -> after i2c disable: 12.61, delta: 0.00
    Setting up deep sleep.
    -> after alarm setup: 12.61, delta: 0.00

Interesting conclusions:

- Import handling takes 3s
- Memory read / write at the begining only takes 10ms
- Battery process read only takes 10ms
- Wake time until i2c is initialized (must be > 3s for AM2320 to work): 4.4s
- Wake time until Buttons are read for hold/non-hold state: 7.5s
- Drawing the background only takes 10ms
- Drawing the graph takes no time at all (fishy?)

Sequence:

1. Boot process (empirically measured):  1.3s
2. Imports:                              3.0s
3. BME280 temperature + humidity read:   0.3s
4. AM2320 temperature + humidity read:   0.5s
5. TMF8821 distance read (oversampled):  1.8s
6. eInk display initialization:          0.1s
7. Font loading:                         0.4s
8. Text drawing (temperatures etc):      2.3s
9. Messages drawing (both lines):        1.9s
10. Display refresh:                     0.8s

The following parts can be speed up:

- distance readings can be reduced by 0.8s
- messages aren't drawn in a calibrated system (-1.9s)

## 07.01.2023 -- *TOF FoV*

Bottom diameter = 90mm
Distance to bottom = 110mm

Field-of-view Angle = 2 * tan-1((diameter / 2) / distance) = 44.4°

Either: 3x3 normal, 4x4 narrow, 4x4 normal with reduction to center 4,

Seen from the top (sensor below the PCB) and with the holes on the lower side, the SPAD configuration of 3x3_normal is projected away from the angle of view as follows:
+---------+
| 3  2  1 |
| 6  5  4 |
| 9  8  7 |
+---------+

# Open Issues

- [ ] Check accuracy of 1x vs 5x oversampling --> test with sourdough surface
- [ ] Measure current -- toggle lines to drive eInk low
