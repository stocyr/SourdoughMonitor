# from displayio import Bitmap
from math import floor, ceil


# from displayio import Font


class GraphPlot:
    ytick_margin_percentage = 1.05
    ytick_height_separation_factor = 1.2
    ytick_mantissa_steps = [2.0, 2.5, 5.0, 10.0]
    yticks_length = 3


    def __init__(self, bitmap, origin: tuple, top_right: tuple, font, line_color: int, yticks_color: int,
                 font_color: int, line_width: int = 2, background_color: int = 0, font_height=None):
        self.bitmap = bitmap
        self.origin = origin
        self.top_right = top_right
        self.font = font
        self.line_color = line_color
        self.yticks_color = yticks_color
        self.font_color = font_color
        self.line_width = line_width
        self.background_color = background_color
        self.font_height = font_height or self.font.height()

        self.graph_height = self.top_right[1] - self.origin[1]
        self.graph_width = self.top_right[0] - self.origin[0]

        self.max_n_yticks = abs(self.graph_height) / (self.ytick_height_separation_factor * self.font_height)

        self.max_data_with_margin = None
        self.min_data_with_margin = None
        self.data_range_with_margin_to_pixel_factor = None
        self.ytick_separation = None
        self.first_ytick = None
        self.last_ytick = None


    def _setup_yscale(self, data_array: list):
        # First determine data range
        max_data = max(data_array)
        self.max_data_with_margin = max_data * self.ytick_margin_percentage
        min_data = min(data_array)
        self.min_data_with_margin = min_data * (1 / self.ytick_margin_percentage)
        data_range_with_margin = self.max_data_with_margin - self.min_data_with_margin
        self.data_range_with_margin_to_pixel_factor = self.graph_width / data_range_with_margin

        # Define ordinate labels
        min_ytick_data_separation = data_range_with_margin / self.max_n_yticks
        # Move this value into range [1, 10)
        decimal_factor = 10.0
        while min_ytick_data_separation * decimal_factor >= 10.0:
            decimal_factor *= 0.1
        # Now we decomposed the value into mantissa (min_ytick_data_separation * decimal_factor) and exponent
        # (1 / decimal_factor)
        mantissa_value = min_ytick_data_separation * decimal_factor
        # Round this value up to the next higher step in self.ytick_steps
        mantissa_step = 1.0
        for step in self.ytick_mantissa_steps:
            if step > mantissa_value:
                mantissa_step = step
                break  # next-higher value found -> stop search

        self.ytick_separation = mantissa_step / decimal_factor
        self.first_ytick_factor = ceil(self.min_data_with_margin / self.ytick_separation)
        self.last_ytick_factor = floor(self.max_data_with_margin / self.ytick_separation)


    def y_data_to_pixel(self, y_value, compensation=0):
        return round((y_value - self.min_data_with_margin) * self.data_range_with_margin_to_pixel_factor + compensation)


    def x_data_to_pixel(self, x_value):
        return x_value + self.origin[0]


    def _plot_line(self, data_array: list):
        # If we plot an even number of pixels thick, the line's center is offset by -0.5 pixel downward -> precorrect
        compensate_even_thickness = (1 - (self.line_width % 2)) * 0.5 * self.data_range_with_margin_to_pixel_factor
        current_pixel_value_y = self.y_data_to_pixel(data_array[0], compensate_even_thickness)
        for x_value in range(len(data_array) - 1):
            next_pixel_value_y = self.y_data_to_pixel(data_array[x_value + 1], compensate_even_thickness)
            for y_offset in range(- (self.line_width // 2), (self.line_width - 1) // 2 + 1):
                # bitmaptools.draw_line(self.bitmap, x_value, current_pixel_value_y + y_offset,
                #                      x_value + 1, next_pixel_value_y + y_offset, self.line_color)
                print(x_value, current_pixel_value_y + y_offset, x_value + 1, next_pixel_value_y + y_offset)

            current_pixel_value_y = next_pixel_value_y


    def _draw_yticks_and_labels(self):
        for factor in range(self.first_ytick_factor, self.last_ytick_factor + 1):
            y = self.y_data_to_pixel(self.ytick_separation * factor)
            # bitmaptools.draw_line(self.bitmap, self.origin[0], y, self.origin[0] + self.yticks_length, y,
            #                       self.yticks_color)
            # TODO: textfont
            print(self.origin[0], y, self.origin[0] + self.yticks_length, y)


    def plot_graph(self, data_array: list, clear_first=False):
        if clear_first:
            self.bitmap.fill(self.background_color)

        self._setup_yscale(data_array)
        self._plot_line(data_array)
        self._draw_yticks_and_labels()


if __name__ == '__main__':
    test_array = [101.1, 99.2, 104.8, 125.4, 153.0]
    graph = GraphPlot(None, (10, 118), (118, 10), None, 255, 120, 120, 3, 0, 6)
    graph.plot_graph(test_array)
