"""
BME280
"""
import time
import board
import alarm
import busio
import microcontroller
import displayio
import digitalio
import adafruit_bme280.advanced as adafruit_bme280
from adafruit_lc709203f import LC709203F, PackSize
from utils.oled import full_width_display
import neopixel

#pixel = neopixel.NeoPixel(board.NEOPIXEL, 1)
#pixel.deinit()


np_power = digitalio.DigitalInOut(board.NEOPIXEL_POWER)
i2c_power = digitalio.DigitalInOut(board.I2C_POWER)


def set_to_nondefault(pin):
    pin.switch_to_input()
    default_state = pin.value
    pin.switch_to_output(value=not default_state)


np_power.switch_to_output(value=True)
set_to_nondefault(i2c_power)

display = full_width_display()


battery_monitor = LC709203F(board.I2C())
battery_monitor.pack_size = PackSize.MAH1000

i2c = board.I2C()
bme280 = adafruit_bme280.Adafruit_BME280_I2C(i2c)

bme280.mode = adafruit_bme280.MODE_FORCE
bme280.iir_filter = adafruit_bme280.IIR_FILTER_DISABLE
bme280.overscan_temperature = adafruit_bme280.OVERSCAN_X16

print('\n' * 5)
print(f'Time: {time.monotonic():.1f}s')
print(f'Temp: {bme280.temperature:.2f}°')
per, vol = battery_monitor.cell_percent, battery_monitor.cell_voltage
print(f'Battery: {per:.0f}% ({vol:.2f}V)')

time.sleep(4)

displayio.release_displays()

# Disable power to NEOPIXEL
np_power.switch_to_input()
# Disable power to I2C bus
i2c_power.switch_to_input()

al = alarm.time.TimeAlarm(monotonic_time=time.monotonic() + 5)
# This does not return -- it sleeps 20 seconds and then restarts from top
alarm.exit_and_deep_sleep_until_alarms(al)
# We will never get *here*
