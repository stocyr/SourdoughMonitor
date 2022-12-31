from math import floor, ceil

try:
    import bitmaptools

    NO_BITMAPTOOLS = False
except:
    NO_BITMAPTOOLS = True
    pass

import displayio
from adafruit_display_text import bitmap_label
from adafruit_displayio_layout.widgets.widget import Widget

BLACK = 0x202020
DARK = 0x606060
BRIGHT = 0xA0A0A0
WHITE = 0xE0E0E0


def get_font_height(font, scale: int):
    return 5, 7
    if hasattr(font, "get_bounding_box"):
        font_height = int(scale * font.get_bounding_box()[1])
        font_width = int(scale * font.get_bounding_box()[0])
    elif hasattr(font, "ascent"):
        font_height = int(scale * font.ascent + font.ascent)
        font_width = 12
    else:
        font_height = 12
        font_width = 12
    return font_width, font_height


class PaletteColor:
    transparent = 0
    black = 1
    dark_gray = 2
    light_gray = 3
    white = 4


    def __len__(self):
        return 5


class GraphPlot(Widget):
    ytick_margin_percentage = 1.025
    ytick_height_separation_factor = 1.8
    ytick_mantissa_steps = [2.0, 2.5, 5.0, 10.0]
    yticks_length = 2


    def __init__(self,
                 width: int,
                 height: int,
                 origin: tuple,
                 top_right: tuple,
                 font,
                 line_color: int,
                 yticks_color: int,
                 font_color: int,
                 line_width: int = 2,
                 background_color: int = PaletteColor.transparent,
                 ygrid_color: int = None,
                 **kwargs):
        super().__init__(**kwargs)

        self.dry = NO_BITMAPTOOLS
        self._width = width
        self._height = height
        self._plot_bitmap = displayio.Bitmap(self._width, self._height, 5)
        self._plot_bitmap.fill(PaletteColor.transparent)
        self.origin = origin  # tuple of (x, y)
        self.top_right = top_right  # tuple of (x, y)
        self.font = font
        self.line_color = line_color
        self.ygrid_color = ygrid_color
        self.yticks_color = yticks_color
        self.font_color = font_color
        self.line_width = line_width
        self.background_color = background_color

        self._font_width, self._font_height = get_font_height(font, 1)

        self.graph_height = self.top_right[1] - self.origin[1]
        self.graph_width = self.top_right[0] - self.origin[0]

        self.max_n_yticks = abs(self.graph_height) / (self.ytick_height_separation_factor * self._font_height)

        self.max_data_with_margin = None
        self.min_data_with_margin = None
        self.data_range_with_margin_to_pixel_factor = None
        self.ytick_separation = None
        self.first_ytick = None
        self.last_ytick = None

        # Setup palette
        self._palette = displayio.Palette(5)
        self._palette.make_transparent(0)
        self._palette[1] = BLACK
        self._palette[2] = DARK
        self._palette[3] = BRIGHT
        self._palette[4] = WHITE

        self._screen_tilegrid = displayio.TileGrid(self._plot_bitmap, pixel_shader=self._palette, x=0, y=0)

        self.append(self._screen_tilegrid)


    def _setup_yscale(self, data_array: list):
        # First determine data range
        max_data = max(data_array)
        self.max_data_with_margin = max_data * self.ytick_margin_percentage
        min_data = min(data_array)
        self.min_data_with_margin = min_data * (2 - self.ytick_margin_percentage)
        data_range_with_margin = self.max_data_with_margin - self.min_data_with_margin
        self.data_range_with_margin_to_pixel_factor = self.graph_height / data_range_with_margin

        # Define ordinate labels
        min_ytick_data_separation = data_range_with_margin / self.max_n_yticks
        # Move this value into range [1, 10)
        self.decimal_factor = 10.0
        while min_ytick_data_separation * self.decimal_factor >= 10.0:
            self.decimal_factor *= 0.1
        # Now we decomposed the value into mantissa (min_ytick_data_separation * decimal_factor) and exponent
        # (1 / decimal_factor)
        mantissa_value = min_ytick_data_separation * self.decimal_factor
        # Round this value up to the next higher step in self.ytick_mantissa_steps
        mantissa_step = 1.0
        for step in self.ytick_mantissa_steps:
            if step > mantissa_value:
                mantissa_step = step
                break  # next-higher value found -> stop search

        self.ytick_separation = mantissa_step / self.decimal_factor
        self.first_ytick_factor = ceil(self.min_data_with_margin / self.ytick_separation)
        self.last_ytick_factor = floor(self.max_data_with_margin / self.ytick_separation)


    def y_data_to_pixel(self, y_value, compensation=0):
        return round((y_value - self.min_data_with_margin) * self.data_range_with_margin_to_pixel_factor +
                     compensation) + self.origin[1]


    def x_data_to_pixel(self, x_value):
        return x_value + self.origin[0]


    def _plot_line(self, data_array: list, stretch=False):
        # If we plot an even number of pixels thick, the line's center is offset by -0.5 pixel downward -> precorrect
        compensate_even_thickness = (1 - (self.line_width % 2)) * 0.5 * self.data_range_with_margin_to_pixel_factor
        advance_x = 1 if not stretch else self.graph_width / (len(data_array) - 1)
        current_pixel_value_y = self.y_data_to_pixel(data_array[0], compensate_even_thickness)
        current_pixel_value_x = self.origin[0]
        for x_value in range(len(data_array) - 1):
            next_pixel_value_y = self.y_data_to_pixel(data_array[x_value + 1], compensate_even_thickness)
            next_pixel_value_x = round(current_pixel_value_x + advance_x)
            for y_offset in range(- (self.line_width // 2), (self.line_width - 1) // 2 + 1):
                if not self.dry:
                    bitmaptools.draw_line(self._plot_bitmap, current_pixel_value_x, current_pixel_value_y + y_offset,
                                          next_pixel_value_x, next_pixel_value_y + y_offset, self.line_color)
                else:
                    print(current_pixel_value_x, current_pixel_value_y + y_offset,
                          next_pixel_value_x, next_pixel_value_y + y_offset)
            # print()

            current_pixel_value_y = next_pixel_value_y
            current_pixel_value_x = next_pixel_value_x


    def _draw_yticks_and_labels(self):
        for factor in range(self.first_ytick_factor, self.last_ytick_factor + 1):
            y = self.y_data_to_pixel(self.ytick_separation * factor)
            precision = 1 if self.decimal_factor > 1 else 0
            tick_text = '{1:.{0}f}'.format(precision, self.ytick_separation * factor)

            estimated_text_width = len(tick_text) * self._font_width
            if not self.dry:
                bitmaptools.draw_line(self._plot_bitmap, self.origin[0] - self.yticks_length, y, self.origin[0], y,
                                      self.yticks_color)
                if self.ygrid_color is not None:
                    bitmaptools.draw_line(self._plot_bitmap, self.origin[0] + 1, y, self.top_right[0], y,
                                          self.ygrid_color)
            else:
                print(self.origin[0], y, self.origin[0] + self.yticks_length, y)
            tick_text = bitmap_label.Label(
                self.font,
                color=self._palette[self.font_color],
                text=tick_text,
                x=self.origin[0] - self.yticks_length - estimated_text_width - 3,
                y=y,
            )
            self.append(tick_text)


    def plot_graph(self, data_array: list, clear_first=False):
        if clear_first:
            self._plot_bitmap.fill(self.background_color)

        self._setup_yscale(data_array)
        self._draw_yticks_and_labels()
        self._plot_line(data_array, stretch=True)


if __name__ == '__main__':
    from adafruit_bitmap_font import bitmap_font

    tick_font = bitmap_font.load_font("00Starmap-11-11.bdf")
    test_array = [101.1, 99.2, 104.8, 125.4, 153.0]
    graph = GraphPlot(128, 128, (20, 118), (118, 10), tick_font, PaletteColor.light_gray, PaletteColor.light_gray,
                      PaletteColor.light_gray, 3, PaletteColor.white, 6)
    graph.plot_graph(test_array)
