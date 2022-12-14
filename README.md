SourdoughMonitor
================
Sourdough monitoring system with an ESP32 feather board, a ToF distance sensor and onboard temperature/humidity sensors.

Setup
-----

### Hardware

![](imgs/adafruit_products_Adafruit_Feather_ESP32-S2_Pinout.png)

We use the [ESP32-S2 with BME280](https://circuitpython.org/board/adafruit_feather_esp32s2_bme280/).

Attached to it are the following devices:

- **TMF8821** TimeOfFlight distance sensor on i2c address `0x41`
  . [Link](https://shop.pimoroni.com/products/sparkfun-qwiic-mini-dtof-imager-tmf8821?variant=39880899067987)
- **ThinkInk 2.9" grayscale** e-Ink display with 296x128 pixels and four gray scales
  . [Product](https://shop.pimoroni.com/products/adafruit-2-9-grayscale-eink-epaper-display-featherwing-4-level-grayscale?variant=32283947728979)
  , [Pinouts](https://cdn-learn.adafruit.com/assets/assets/000/096/234/original/adafruit_products_FeatherWing_bb.jpg?1603386177)
  , [Button Pinout](https://cdn-learn.adafruit.com/assets/assets/000/104/602/original/eink___epaper_Pinouts_FeatherWing_Buttons.jpg?1631640413)
  , [FeatherWing Pinout](https://cdn-learn.adafruit.com/assets/assets/000/104/601/original/eink___epaper_Pinouts_2.9.jpg?1631640290)
- **BME280** on-board temperature, humidity, pressure and altitude sensor on i2c address `0x77`
  . [Manual](https://cdn.shopify.com/s/files/1/0174/1800/files/bst-bme280-ds002.pdf?v=1662743150)
  , [Product](https://shop.pimoroni.com/products/bme280-breakout?variant=29420960677971)
- **AM2320** external temperature and humidity sensor on i2c address `0x5c`
  . [Datasheet](https://akizukidenshi.com/download/ds/aosong/AM2320.pdf)
  , [Product](https://shop.pimoroni.com/products/digital-temperature-and-humidity-sensor?variant=35611648138)
- **Zio OLED** 1.5" display with 128x128 pixel for debugging on i2c address `0x3c`
  . [Link](https://learn.adafruit.com/adafruit-grayscale-1-5-128x128-oled-display)
- **U132** passive buzzer for signalling on GPIO pin <tbd>
  . [Schematic](https://cdn.shopify.com/s/files/1/0174/1800/products/buzzer_sch_01_1500x1500.jpg?v=1640774058)
  , [Product](https://shop.pimoroni.com/products/passive-buzzer-unit?variant=39618442297427)
- **LC709203** on-board LiPo battery monitor on i2c address `0x0b`
  . [Datasheet](https://cdn-learn.adafruit.com/assets/assets/000/094/597/original/LC709203F-D.PDF?1599248750)
  , [Product](https://learn.adafruit.com/adafruit-esp32-s2-tft-feather/i2c-on-board-sensor)

For the other on-board peripheries, the
guide [here](https://learn.adafruit.com/adafruit-esp32-s2-feather/circuitpython-essentials) provides tutorials. Also,
the schematic can be downloaded [here](https://learn.adafruit.com/assets/109937)

### Programming Language

We work with Python, specifically CircuitPython 7.3.2.

### IDE

We work with PyCharm CircuitPython, a guide to setting it up to work with circuitpythyon can be found  [here]
(https://learn.adafruit.com/welcome-to-circuitpython/pycharm-and-circuitpython).
Since CircuitPython 7.3.2 is forked from the latest MicroPython repository which
uses [Python <= 3.9 features] (https://docs.micropython.org/en/latest/genrst/index.html), we create a virtual  
environment with Python 3.9 and install the `circuitpython-stubs` as well as the
[_Serial Port Monitor_](https://plugins.jetbrains.com/plugin/8031-serial-port-monitor) plugin.

The CircuitPython libraries we use are the following (can be installed on the local `venv` as well to enhance code
completion):

- `adafruit-circuitpython-am2320` for AM2320 (temp sensor)
  . [Example](https://github.com/adafruit/Adafruit_CircuitPython_AM2320/blob/main/examples/am2320_simpletest.py)
- `adafruit-circuitpython-bme280` for BME280 (environment sensor)
  . [Example](https://github.com/adafruit/Adafruit_CircuitPython_BME280/blob/main/examples/bme280_normal_mode.py)
- `adafruit-circuitpython-lc709203f` for LC709203 (battery monitor)
  . [Example](https://github.com/adafruit/Adafruit_CircuitPython_LC709203F/blob/main/examples/lc709203f_simpletest.py)
- `adafruit-circuitpython-il0373` for IL0373 (e-Ink display)
  . [Example](https://github.com/adafruit/Adafruit_CircuitPython_IL0373/blob/main/examples/il0373_2.9_grayscale.py)
- `` for TMF8821 (ToF sensor). [Example]()
- `adafruit-circuitpython-ssd1327` for
  SSD1327. [Example](https://github.com/adafruit/Adafruit_CircuitPython_SSD1327/blob/main/examples/ssd1327_simpletest.py)
- `adafruit-circuitpython-simpleio` for PWM
- `adafruit-circuitpython-ticks` for time measurements in TMF882X driver
- `adafruit-circuitpython-typing` for datatype description in TMF882X driver
- `circuitpython-displayio-cartesian` for plotting on the display

Libraries
---------

To install the backend libraries for use of the periphery devices, the following files must be copies into the `/lib`
folder of the CIRCUITPYTHON volume (
from [here](https://github.com/adafruit/Adafruit_CircuitPython_Bundle/releases/tag/20220904)):

- `adafruit_ssd1327.mpy`
- `adafruit_display_text/` folder
- `simpleio.mpy` (for PWM on the buzzer pin)
- `neopixel.mpy`
- `adafruit_ticks.mpy` (for millisecond time measurement)

Hardware Limitations
--------------------

We don't want to use Button C on the eInk display since pulling it high would result in a constant current through the
onboard LED.


Usage
-----


Further reading
---------------

https://github.com/todbot/circuitpython-tricks
