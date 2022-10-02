"""
Display experiment
"""
import time

import alarm
import board
import busio
import digitalio
import displayio
import terminalio
import adafruit_bme280.advanced as adafruit_bme280
import adafruit_il0373
from adafruit_bitmap_font import bitmap_font
from adafruit_display_text import label
from adafruit_lc709203f import LC709203F, PackSize

from utils.oled import full_width_display

displayio.release_displays()

#display = full_width_display()


# This pinout works on a Feather M4 and may need to be altered for other boards.
spi = busio.SPI(board.SCK, board.MOSI)  # Uses SCK and MOSI
epd_cs = board.D9
epd_dc = board.D10

display_bus = displayio.FourWire(
    spi, command=epd_dc, chip_select=epd_cs, baudrate=1000000
)
time.sleep(1)

display = adafruit_il0373.IL0373(display_bus, width=296, height=128, rotation=270, black_bits_inverted=False,
                                 color_bits_inverted=False, grayscale=True, refresh_time=1, border=None)

battery_monitor = LC709203F(board.I2C())
battery_monitor.pack_size = PackSize.MAH1000

i2c = board.I2C()
bme280 = adafruit_bme280.Adafruit_BME280_I2C(i2c)
bme280.mode = adafruit_bme280.MODE_FORCE
bme280.iir_filter = adafruit_bme280.IIR_FILTER_DISABLE
bme280.overscan_temperature = adafruit_bme280.OVERSCAN_X16


my_group = displayio.Group()

BLACK = 0x202020
DARK = 0x606060
BRIGHT = 0xA0A0A0
WHITE = 0xE0E0E0

# White background
bg_bitmap = displayio.Bitmap(display.width, display.height, 1)
single_color_palette = displayio.Palette(1)
single_color_palette[0] = WHITE
bg_sprite = displayio.TileGrid(bg_bitmap, pixel_shader=single_color_palette, x=0, y=0)
my_group.append(bg_sprite)

# Large text field
temperature_text = f'{bme280.temperature:.2f}°'
font_large = bitmap_font.load_font("SegoeUI_semibold-105.bdf")
text_area_large = label.Label(font_large, text=temperature_text, color=BLACK)
text_area_large.x = -2
text_area_large.y = display.height // 2 - 5
my_group.append(text_area_large)

# Small text field
per, vol = battery_monitor.cell_percent, battery_monitor.cell_voltage
monitoring_text = f'Battery: {per:.0f}% ({vol:.2f}V)'
font_small = terminalio.FONT
text_area_small = label.Label(font_small, text=monitoring_text, color=DARK)
text_area_small.x = display.width // 2 - 60
text_area_small.y = 118
my_group.append(text_area_small)

# Show it
display.show(my_group)
display.refresh()


while True:
    pass
