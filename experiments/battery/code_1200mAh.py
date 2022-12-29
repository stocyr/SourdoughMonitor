# SPDX-FileCopyrightText: 2022 Kattni Rembor for Adafruit Industries
# SPDX-License-Identifier: MIT
"""
CircuitPython Simple Example for LC709203 Sensor
"""
import time
import board
import digitalio
from adafruit_lc709203f import LC709203F, LC709203F_CMD_APA

from utils.oled import repl_to_oled

repl_to_oled()


def override_packsize(lc709203f: LC709203F, value: int):
    assert value == 1200
    lc709203f._write_word(LC709203F_CMD_APA, 0x1D)


# Set up PED
led = digitalio.DigitalInOut(board.LED)
led.switch_to_output()

# Set up file system write enable switch on A0
switch = digitalio.DigitalInOut(board.A0)
switch.direction = digitalio.Direction.INPUT
switch.pull = digitalio.Pull.UP


# Create sensor object, using the board's default I2C bus.
battery_monitor = LC709203F(board.I2C())

# Interpolated the APA value of 1000mAh and 2000mAh to match the value for a 1200mAh battery
override_packsize(battery_monitor, 1200)

print(f'A0 state: {switch.value}')
if switch.value:
    print('uC R/O')
else:
    print('uC W!')

t_start = time.time()
try:
    with open("/battery_1200mAh.log", "a") as fp:
        while True:
            per, vol = battery_monitor.cell_percent, battery_monitor.cell_voltage
            print(f'Bat {per:.2f}%, {vol:.2f}V')
            fp.write(f'{time.time() - t_start},{per:.2f},{vol:.2f}\n')
            fp.flush()
            led.value = not led.value
            time.sleep(2)
except OSError as e:  # Typically when the filesystem isn't writeable...
    if e.args[0] == 28:  # If the file system is full...
        print('File system full!')
        delay = 0.1  # ...blink the LED faster!
    else:
        print('Write protected')
        delay = 0.25  # ...blink the LED every half second.
    while True:
        led.value = not led.value
        time.sleep(delay)
