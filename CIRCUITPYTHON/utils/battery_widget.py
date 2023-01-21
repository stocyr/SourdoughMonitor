import displayio
from adafruit_displayio_layout.widgets import rectangle_helper
from adafruit_displayio_layout.widgets.widget import Widget

from utils.eink_constants import PaletteColor, eink_palette

BLACK = 0x202020
DARK = 0x606060
BRIGHT = 0xA0A0A0
WHITE = 0xE0E0E0


class BatteryWidget(Widget):
    ytick_margin_percentage = 1.025
    ytick_height_separation_factor = 1.8
    ytick_mantissa_steps = [2.0, 2.5, 5.0, 10.0]
    yticks_length = 2


    def __init__(self,
                 upper_part_height: int,
                 upper_part_width: int,
                 background_color: int = PaletteColor.dark_gray,
                 fill_color: int = PaletteColor.black,
                 exclamation_mark: tuple = (5, 2, 8, 7, 2),
                 exclamation_mark_threshold: float = 0.038,
                 exclamation_mark_color: int = PaletteColor.black,
                 **kwargs):
        super().__init__(**kwargs)

        self.upper_part_height = upper_part_height
        self.upper_part_width = upper_part_width
        self.background_color = background_color
        self.fill_color = fill_color
        self.exclamation_mark = exclamation_mark
        self.exclamation_mark_threshold = exclamation_mark_threshold
        self.exclamation_mark_color = exclamation_mark_color

        self.lower_part_height = self.height - upper_part_height
        self.upper_part_percentage = self.lower_part_height / self.height
        self.x_upper_begin = round((self.width - upper_part_width) / 2)

        # Setup palette
        self._palette = eink_palette
        self._palette.make_transparent(0)
        self._palette[1] = BLACK
        self._palette[2] = DARK
        self._palette[3] = BRIGHT
        self._palette[4] = WHITE

        self._bitmap = displayio.Bitmap(self.width, self.height, 5)
        self._bitmap.fill(PaletteColor.transparent)
        self._tilegrid = displayio.TileGrid(self._bitmap, pixel_shader=self._palette, x=0, y=0)

        self.append(self._tilegrid)

        self.critical_battery = False


    def draw(self, percentage: float):
        self.critical_battery = False
        self._bitmap.fill(PaletteColor.transparent)
        fill_px = round(self._height * percentage)
        # Fill lower part
        rectangle_helper(0, self.height,
                         -min(self.lower_part_height, fill_px), self.width,
                         self._bitmap, self.fill_color, self._palette, True)
        if percentage > self.upper_part_percentage:
            # Fill upper part
            rectangle_helper(self.x_upper_begin, self.height - self.lower_part_height,
                             -(fill_px - self.lower_part_height), self.upper_part_width,
                             self._bitmap, self.fill_color, self._palette, True)
            # Fill potential background of upper part
            if fill_px < self.height:
                rectangle_helper(self.x_upper_begin, self.height - fill_px,
                                 -(self.height - fill_px), self.upper_part_width,
                                 self._bitmap, self.background_color, self._palette, True)
        else:
            # Fill part of the lower part with background
            rectangle_helper(0, self.height - fill_px,
                             -(self.lower_part_height - fill_px), self.width,
                             self._bitmap, self.background_color, self._palette, True)
            # Fill upper part with background
            rectangle_helper(self.x_upper_begin, self.height - self.lower_part_height,
                             -self.upper_part_height, self.upper_part_width,
                             self._bitmap, self.background_color, self._palette, True)

        if percentage <= self.exclamation_mark_threshold:
            self.critical_battery = True
            y_dot, width_dot, y_stem, height_stem, width_stem = self.exclamation_mark
            x_dot = round((self.width - width_dot) / 2)
            x_stem = round((self.width - width_stem) / 2)
            # Exclamation mark dot
            rectangle_helper(x_dot, self.height - y_dot,
                             -width_dot, width_dot,
                             self._bitmap, self.exclamation_mark_color, self._palette, True)
            rectangle_helper(x_stem, self.height - y_stem,
                             -height_stem, width_stem,
                             self._bitmap, self.exclamation_mark_color, self._palette, True)


if __name__ == '__main__':
    while True:
        direction = 'up'
        percentage = 0
        while True:
            if direction == 'up':
                percentage += 0.05
                if percentage > 1.0:
                    percentage = 1.0
                    direction = 'down'
            else:
                percentage -= 0.05
                if percentage < 0.0:
                    percentage = 0.0
                    direction = 'up'
            # battery_symbol.draw(perc)
            # display.refresh()
            # time.sleep(0.07)
