import time

t_start = time.monotonic()

import alarm
import digitalio
import adafruit_bme280.advanced as adafruit_bme280
import board
import displayio
import time
import busio

from adafruit_bitmap_font import bitmap_font

from GraphPlot import GraphPlot, PaletteColor
import adafruit_il0373

displayio.release_displays()

np_power = digitalio.DigitalInOut(board.NEOPIXEL_POWER)
i2c_power = digitalio.DigitalInOut(board.I2C_POWER)

# Disable power to NEOPIXEL
np_power.switch_to_input()

# Re-enable I2C from low power mode
i2c_power.switch_to_input()
default_state = i2c_power.value
i2c_power.switch_to_output(value=not default_state)

# Initialize e-Ink display
with busio.SPI(board.SCK, board.MOSI) as spi:
    epd_cs = board.D9
    epd_dc = board.D10
    display_bus = displayio.FourWire(spi, command=epd_dc, chip_select=epd_cs, baudrate=1000000)
    time.sleep(0.1)
    display = adafruit_il0373.IL0373(display_bus, width=296, height=128, rotation=270, black_bits_inverted=False,
                                     color_bits_inverted=False, grayscale=True, refresh_time=1, border=None)

    # Initialize temperature sensor
    i2c = board.I2C()
    bme280 = adafruit_bme280.Adafruit_BME280_I2C(i2c)
    bme280.mode = adafruit_bme280.MODE_FORCE
    bme280.iir_filter = adafruit_bme280.IIR_FILTER_DISABLE
    bme280.overscan_temperature = adafruit_bme280.OVERSCAN_X16
    bme280.overscan_humidity = adafruit_bme280.OVERSCAN_X4

    # Need to read twice: https://learn.adafruit.com/adafruit-bme280-humidity-barometric-pressure-temperature-sensor-breakout/f-a-q#faq-2958150
    dummy_read = bme280.temperature
    temperature = bme280.temperature

    # Fonts used for the y-tick labels
    tick_font = bitmap_font.load_font("00Starmap-11-11.bdf")

    # Main display group
    g = displayio.Group()

    # Load background bitmap
    f_bg = open("bg_simple.bmp", "rb")
    pic = displayio.OnDiskBitmap(f_bg)
    t = displayio.TileGrid(pic, pixel_shader=pic.pixel_shader)
    g.append(t)

    # Add the graph plot
    plot = GraphPlot(
        width=296, height=128, origin=(25, 116), top_right=(285, 35), font=tick_font, line_color=PaletteColor.black,
        yticks_color=PaletteColor.dark_gray, font_color=PaletteColor.dark_gray, line_width=3,
        background_color=PaletteColor.transparent, ygrid_color=PaletteColor.light_gray)
    # percentage_array = [100, 99.2, 127, 110.5, 104.8, 125.4, 153.0, 150.3]
    temp_array = [22.35, 21.5, 22.03, 23.1, 23.5, 22.95, 23.55, 22.9]
    plot.plot_graph(temp_array)
    g.append(plot)

    display.show(g)
    display.refresh()

    # Prepare for low power deep sleep
    displayio.release_displays()

f_bg.close()

# Disable power to I2C bus
i2c_power.switch_to_input()

al = alarm.time.TimeAlarm(monotonic_time=t_start + 3 * 60)
# This does not return -- it sleeps 20 seconds and then restarts from top
alarm.exit_and_deep_sleep_until_alarms(al)
# We will never get *here*
