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

def set_low_power(lowpower: bool = True):
    # Disable power to NEOPIXEL
    np_power = digitalio.DigitalInOut(board.NEOPIXEL_POWER)
    np_power.switch_to_output(lowpower)
    if lowpower:
        np_power.value = False

    # Disable power to I2C bus
    i2c_power = digitalio.DigitalInOut(board.I2C_POWER)
    i2c_power.switch_to_output(lowpower)
    if lowpower:
        i2c_power.value = False

    # Disable power to 3v3 regulator
    v33_power = digitalio.DigitalInOut(board.EN)
    v33_power.switch_to_output(lowpower)
    if lowpower:
        v33_power.value = False

set_low_power(False)

display = full_width_display()


battery_monitor = LC709203F(board.I2C())
battery_monitor.pack_size = PackSize.MAH1000

i2c = board.I2C()
bme280 = adafruit_bme280.Adafruit_BME280_I2C(i2c)

bme280.mode = adafruit_bme280.MODE_FORCE
bme280.iir_filter = adafruit_bme280.IIR_FILTER_DISABLE
bme280.overscan_temperature = adafruit_bme280.OVERSCAN_X16

print(f'Time: {time.monotonic():.1f}s')
print(f'Temp: {bme280.temperature:.2f}°')
per, vol = battery_monitor.cell_percent, battery_monitor.cell_voltage
print(f'Battery: {per:.0f}% ({vol:.2f}V)')

set_low_power

al = alarm.time.TimeAlarm(monotinic_time=time.monotonic() + 20)
# This does not return -- it sleeps 20 seconds and then restarts from top
alarm.exit_and_deep_sleep_until_alarms(al)
# We will never get *here*
