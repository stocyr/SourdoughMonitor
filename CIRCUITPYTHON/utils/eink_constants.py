import displayio

BLACK = 0x202020
DARK = 0x606060
BRIGHT = 0xA0A0A0
WHITE = 0xE0E0E0


class PaletteColor:
    transparent = 0
    black = 1
    dark_gray = 2
    light_gray = 3
    white = 4


    def __len__(self):
        return 5


eink_palette = displayio.Palette(5)
eink_palette.make_transparent(0)
eink_palette[1] = BLACK
eink_palette[2] = DARK
eink_palette[3] = BRIGHT
eink_palette[4] = WHITE
