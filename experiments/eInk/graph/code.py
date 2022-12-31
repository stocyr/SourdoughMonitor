import board
import displayio
import time
import busio

from adafruit_bitmap_font import bitmap_font

from GraphPlot import GraphPlot, PaletteColor
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

# Fonts used for the Dial tick labels
tick_font = bitmap_font.load_font("00Starmap-11-11.bdf")

# Create different Cartesian widgets
g = displayio.Group()

with open("sketch.bmp", "rb") as f:
    pic = displayio.OnDiskBitmap(f)
    t = displayio.TileGrid(pic, pixel_shader=pic.pixel_shader)
    g.append(t)

plot = GraphPlot(
    296, 128, (22, 114), (282, 31), tick_font, PaletteColor.black, PaletteColor.dark_gray,
    PaletteColor.dark_gray, 3, PaletteColor.transparent)
test_array = [100, 99.2, 104.8, 125.4, 153.0]
plot.plot_graph(test_array)
# g.append(plot)

print(plot.decimal_factor)

display.show(g)  # add high level Group to the display
display.refresh()
while True:
    pass
