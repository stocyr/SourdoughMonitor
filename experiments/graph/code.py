from utils.oled import full_width_display

import board
import displayio
import terminalio
import time
from adafruit_displayio_layout.widgets.cartesian import Cartesian
import bitmaptools

display = full_width_display()


# Fonts used for the Dial tick labels
tick_font = terminalio.FONT


# Create different Cartesian widgets
my_group = displayio.Group()

my_plane = Cartesian(
    x=15,  # x position for the plane
    y=2,  # y plane position
    width=140,  # display width
    height=105,  # display height
    xrange=(0, 10),  # x range
    yrange=(0, 10),  # y range
    subticks=True,
    axes_color=0x888888,
    font_color=0xAAAAAA,
    pointer_color=0xBBBBBB,
    tick_color=0x888888,
    pointer_radius=2,
)

my_plane._screen_palette[4] = 0xFFFFFF

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


my_group = displayio.Group()
my_group.append(my_plane)
display.show(my_group)  # add high level Group to the display

data = [
    # (0, 0),  # we do this point manually - so we have no wait...
    (1, 1),
    (2, 1),
    (2, 2),
    (3, 3),
    (4, 3),
    (4, 4),
    (5, 5),
    (6, 5),
    (6, 6),
    (7, 7),
    (8, 7),
    (8, 8),
    (9, 9),
    (10, 9),
    (10, 10),
]

print("examples/displayio_layout_cartesian_lineplot.py")

# first point without a wait.
my_plane.add_plot_line(0, 0)
for x, y in data:
    my_plot_line(my_plane, x, y)
    #time.sleep(0.5)

while True:
    pass