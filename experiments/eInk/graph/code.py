from utils.oled import full_width_display

import board
import displayio
import terminalio
import time
import busio
from adafruit_displayio_layout.widgets.cartesian import Cartesian
from adafruit_bitmap_font import bitmap_font
import bitmaptools
from adafruit_bitmapsaver import save_pixels

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

BLACK = 0x202020
DARK = 0x606060
BRIGHT = 0xA0A0A0
WHITE = 0xE0E0E0

# Create different Cartesian widgets
my_group = displayio.Group()

# Fill background white
bg_bitmap = displayio.Bitmap(display.width, display.height, 1)
single_color_palette = displayio.Palette(1)
single_color_palette[0] = WHITE
bg_sprite = displayio.TileGrid(bg_bitmap, pixel_shader=single_color_palette, x=0, y=0)
my_group.append(bg_sprite)



my_plane = Cartesian(
    x=18,  # x position for the plane
    y=15,  # y plane position
    width=display.width - 50,  # display width
    height=display.height - 40,  # display height
    xrange=(0, 6),  # x range
    yrange=(0, 6),  # y range
    subticks=True,
    axes_color=DARK,
    font_color=DARK,
    pointer_color=BLACK,
    tick_color=BRIGHT,
    tick_label_font=tick_font,
    background_color=WHITE,
)

my_plane._screen_palette[4] = BLACK

def my_plot_line(cls, x: int, y: int) -> None:
        """add_plot_line function.

        add line to the plane.
        multiple calls create a line-plot graph.

        :param int x: ``x`` coordinate in the local plane
        :param int y: ``y`` coordinate in the local plane
        :return: None

        rtype: None
        """
        cls._add_point(x, y)
        if len(cls.plot_line_point) > 1:
            bitmaptools.draw_line(
                cls._plot_bitmap,
                cls.plot_line_point[-2][0],
                cls.plot_line_point[-2][1],
                cls.plot_line_point[-1][0],
                cls.plot_line_point[-1][1],
                4,
            )
            bitmaptools.draw_line(
                cls._plot_bitmap,
                cls.plot_line_point[-2][0],
                cls.plot_line_point[-2][1] - 1,
                cls.plot_line_point[-1][0],
                cls.plot_line_point[-1][1] - 1,
                4,
            )


my_group.append(my_plane)

data = [
    # (0, 0),  # we do this point manually - so we have no wait...
    (1, 1),
    (2, 1),
    (2, 2),
    (3, 3),
    (4, 3),
    (4, 4),
    (5, 5),
]

# first point without a wait.
my_plane.add_plot_line(0, 0)
for x, y in data:
    my_plot_line(my_plane, x, y)

#save_pixels('screenshot.bmp', display)

display.show(my_group)  # add high level Group to the display
display.refresh()
while True:
    pass