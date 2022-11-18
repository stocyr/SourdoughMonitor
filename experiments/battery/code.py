# SPDX-FileCopyrightText: 2022 Kattni Rembor for Adafruit Industries
# SPDX-License-Identifier: MIT
"""
CircuitPython Simple Example for LC709203 Sensor
"""
import time
import board
import digitalio
from adafruit_lc709203f import LC709203F, LC709203F_CMD_APA, PackSize

from utils.oled import full_width_display

full_width_display()

# Interpolated the APA value of 1000mAh and 2000mAh to match the value for a 1200mAh battery
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


print(f'A0 state: {switch.value}')
if switch.value:
    print('uC is read only!')
else:
    print('uC write enabled!')

t_start = time.time()
try:
    with open("/battery.log", "a") as fp:
        while True:
            seconds = time.time() - t_start
            print(f'{seconds // 3600}h {(seconds % 3600) // 60}m {seconds % 60}s: ', end='')
            battery_monitor.pack_size = PackSize.MAH1000
            battery_monitor.init_RSOC()
            per1000, vol = battery_monitor.cell_percent, battery_monitor.cell_voltage
            print(f'{vol:.3f}V')
            print(f'{per1000:.1f}%,', end='')

            override_packsize(battery_monitor, 1200)
            battery_monitor.init_RSOC()
            per1200, vol = battery_monitor.cell_percent, battery_monitor.cell_voltage
            print(f'{per1200:.1f}%,', end='')

            battery_monitor.pack_size = PackSize.MAH2000
            battery_monitor.init_RSOC()
            per2000, vol = battery_monitor.cell_percent, battery_monitor.cell_voltage
            print(f'{per2000:.1f}%')

            fp.write(f'{time.time() - t_start},{vol:.3f},{per1000:.1f},{per1200:.1f},{per2000:.1f}\n')
            fp.flush()
            led.value = not led.value
            time.sleep(20)
except OSError as e:  # Typically when the filesystem isn't writeable...
    if e.args[0] == 28:  # If the file system is full...
        print('ERROR:\nFile system full!')
        delay = 0.1  # ...blink the LED faster!
    else:
        print('ERROR:\nWrite protected')
        delay = 0.25  # ...blink the LED every half second.
    while True:
        led.value = not led.value
        time.sleep(delay)
