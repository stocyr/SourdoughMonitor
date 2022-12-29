import alarm
import microcontroller
import time
import board
import displayio
import adafruit_ssd1327


def repl_to_oled():
    displayio.release_displays()
    i2c = board.I2C()
    display_bus = displayio.I2CDisplay(i2c, device_address=0x3C)
    display = adafruit_ssd1327.SSD1327(display_bus, width=128, height=128)


# From https://learn.adafruit.com/deep-sleep-with-circuitpython/sleep-memory

# Reset the count if we haven't slept yet.
if not alarm.wake_alarm:
    # Use byte 5 in sleep memory. This is just an example.
    alarm.sleep_memory[5] = 0

alarm.sleep_memory[5] = (alarm.sleep_memory[5] + 1) % 256

# Display the current battery voltage and the count.
print(f"CPU temp: {microcontroller.Processor.temperature}°C")

# Sleep for 60 seconds.
al = alarm.time.TimeAlarm(monotonic_time=time.monotonic() + 60)
alarm.exit_and_deep_sleep_until_alarms(al)
# Does not return. Exits, and restarts after 60 seconds.
