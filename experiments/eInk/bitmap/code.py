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
                                 color_bits_inverted=False, grayscale=True, refresh_time=1, border=None)
g = displayio.Group()

with open("/sketch.bmp", "rb") as f:
    pic = displayio.OnDiskBitmap(f)
    t = displayio.TileGrid(pic, pixel_shader=pic.pixel_shader)
    g.append(t)
    display.show(g)
    display.refresh()
    print("refreshed")
    time.sleep(180)
