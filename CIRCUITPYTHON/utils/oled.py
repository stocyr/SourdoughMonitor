import board
import displayio
import adafruit_ssd1327


def repl_to_oled():
    displayio.release_displays()
    i2c = board.I2C()
    display_bus = displayio.I2CDisplay(i2c, device_address=0x3C)
    display = adafruit_ssd1327.SSD1327(display_bus, width=128, height=128)
