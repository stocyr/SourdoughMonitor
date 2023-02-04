from math import floor, ceil

import bitmaptools
import displayio
from adafruit_display_text import bitmap_label
from adafruit_displayio_layout.widgets.widget import Widget

from utils.eink_constants import PaletteColor, eink_palette


def get_font_height(font, scale: int):
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


class GraphPlot(Widget):
    ytick_margin_percentage = 1.025
    ytick_height_separation_factor = 1.8
    ytick_mantissa_steps = [2.0, 5.0, 10.0]
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
                 font_size: tuple = None,
                 alignment: str = 'fit',
                 dry: bool = False,
                 **kwargs):
        super().__init__(**kwargs)

        self.dry = dry
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
        if font_size is None:
            self._font_width, self._font_height = get_font_height(font, 1)
        else:
            self._font_width, self._font_height = font_size
        self.alignment = alignment

        self.graph_height = self.top_right[1] - self.origin[1]
        self.graph_width = self.top_right[0] - self.origin[0] + 1  # Include leftmost column

        self.max_n_yticks = abs(self.graph_height) / (self.ytick_height_separation_factor * self._font_height)

        self.max_data_with_margin = None
        self.min_data_with_margin = None
        self.data_range_with_margin_to_pixel_factor = None
        self.ytick_separation = None
        self.first_ytick = None
        self.last_ytick = None

        self._palette = eink_palette
        self._screen_tilegrid = displayio.TileGrid(self._plot_bitmap, pixel_shader=self._palette, x=0, y=0)
        self.append(self._screen_tilegrid)


    def _setup_yscale(self, data_array: list):
        # First determine data range
        max_data = max(data_array)
        self.max_data_with_margin = max_data * self.ytick_margin_percentage
        min_data = min(data_array)
        self.min_data_with_margin = min_data * (2 - self.ytick_margin_percentage)

        if max_data == min_data:
            # Work around if data has no range 0:
            self.max_data_with_margin = max_data + 1
            self.min_data_with_margin = min_data - 1
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


    def _draw_yticks_and_labels(self):
        # max_characters = ceil((self.origin[0] - self.yticks_length - 4) / self._font_width)
        for factor in range(self.first_ytick_factor, self.last_ytick_factor + 1):
            y = self.y_data_to_pixel(self.ytick_separation * factor)
            precision = 1 if self.decimal_factor > 1 else 0
            tick_text = '{1:.{0}f}'.format(precision, self.ytick_separation * factor)  # [:max_characters]

            estimated_text_width = len(tick_text) * self._font_width
            if not self.dry:
                bitmaptools.draw_line(self._plot_bitmap, self.origin[0] - self.yticks_length, y, self.origin[0], y,
                                      self.yticks_color)
                if self.ygrid_color is not None:
                    bitmaptools.draw_line(self._plot_bitmap, self.origin[0] + 1, y, self.top_right[0], y,
                                          self.ygrid_color)
            else:
                print(self.origin[0], y, self.origin[0] + self.yticks_length, y)
            x_pos = self.origin[0] - self.yticks_length - estimated_text_width - 4
            tick_label = bitmap_label.Label(
                self.font,
                color=self._palette[self.font_color],
                text=tick_text,
                x=max(1, x_pos),
                y=y,
                background_color=None if x_pos >= 1 else self._palette[PaletteColor.white]
            )
            self.append(tick_label)


    def _plot_line(self, data_array: list, advance: int = 1):
        # If we plot an even number of pixels thick, the line's center is offset by -0.5 pixel downward -> precorrect
        self.compensate_even_thickness = (1 - (self.line_width % 2)) * 0.5 * self.data_range_with_margin_to_pixel_factor
        current_pixel_value_y = self.y_data_to_pixel(data_array[0], self.compensate_even_thickness)
        if self.alignment == 'right':
            current_pixel_value_x = self.top_right[0] - (len(data_array) - 1) * advance
        else:
            current_pixel_value_x = self.origin[0]

        for x_value in range(len(data_array) - 1):
            next_pixel_value_y = self.y_data_to_pixel(data_array[x_value + 1], self.compensate_even_thickness)
            if self.alignment == 'fit':
                next_pixel_value_x = round(self.origin[0] + (x_value + 1) * (self.graph_width - 1) / (len(data_array) -
                                                                                                      1))
            else:
                next_pixel_value_x = current_pixel_value_x + advance
            for y_offset in range(- (self.line_width // 2), (self.line_width - 1) // 2 + 1):
                if not self.dry:
                    bitmaptools.draw_line(self._plot_bitmap, current_pixel_value_x, current_pixel_value_y + y_offset,
                                          next_pixel_value_x, next_pixel_value_y + y_offset, self.line_color)
                else:
                    print(current_pixel_value_x, current_pixel_value_y + y_offset,
                          next_pixel_value_x, next_pixel_value_y + y_offset)

            current_pixel_value_y = next_pixel_value_y
            current_pixel_value_x = next_pixel_value_x

        # If only one data point is available yet, no line was drawn -> plot a single point
        if len(data_array) == 1:
            if not self.dry:
                bitmaptools.draw_line(self._plot_bitmap, current_pixel_value_x,
                                      current_pixel_value_y - (self.line_width // 2),
                                      current_pixel_value_x, current_pixel_value_y + (self.line_width - 1) // 2,
                                      self.line_color)
            else:
                print(current_pixel_value_x, current_pixel_value_y - (self.line_width // 2), current_pixel_value_x,
                      current_pixel_value_y + (self.line_width - 1) // 2)


    def plot_graph(self, data_array: list, zoomed: bool = False, clear_first=False, peak_ind: int = None):
        if clear_first:
            self._plot_bitmap.fill(self.background_color)

        self._setup_yscale(data_array)
        self._draw_yticks_and_labels()
        self._plot_line(data_array, advance=2 if zoomed else 1)


    def plot_peak(self, data_array: list, peak_pos_in_history: int = None, zoomed: bool = False):
        advance = 2 if zoomed else 1
        if peak_pos_in_history * advance + 1 < self.graph_width:
            # Peak ind is not out of plot window
            peak_y_val = data_array[-1 - peak_pos_in_history]
            peak_y_pos = self.y_data_to_pixel(peak_y_val, self.compensate_even_thickness) - 1
            assert self.alignment == 'right'
            peak_x_pos = self.top_right[0] - peak_pos_in_history * advance
            # Draw triangle
            for start_x, start_y, length in zip([0, -1, -1, -2, -2], [-1, -2, -3, -4, -5], [1, 3, 3, 5, 5]):
                bitmaptools.draw_line(self._plot_bitmap, peak_x_pos + start_x, peak_y_pos + start_y,
                                      peak_x_pos + start_x + length - 1, peak_y_pos + start_y, self.line_color)


if __name__ == '__main__':
    from adafruit_bitmap_font import bitmap_font

    tick_font = bitmap_font.load_font("00Starmap-11-11.bdf")
    test_array = [101.1, 99.2, 104.8, 125.4, 153.0]
    graph = GraphPlot(128, 128, (20, 118), (118, 10), tick_font, PaletteColor.light_gray, PaletteColor.light_gray,
                      PaletteColor.light_gray, 3, PaletteColor.white, 6)
    graph.plot_graph(test_array)
