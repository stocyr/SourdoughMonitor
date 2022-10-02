import board
import busio
import displayio
import supervisor
import adafruit_ssd1327


def full_width_display(fast: bool = False) -> adafruit_ssd1327.SSD1327:
    displayio.release_displays()

    if fast:
        i2c = busio.I2C(board.SCL, board.SDA, frequency=400_000)
    else:
        i2c = board.I2C()
    display_bus = displayio.I2CDisplay(i2c, device_address=0x3C)
    display = adafruit_ssd1327.SSD1327(display_bus, width=128, height=128)

    # Create a Group
    empty_group = displayio.Group()
    display.show(None)
    repl_group = display.root_group  # this gets the current root_group, the REPL
    display.show(empty_group)

    # Relocate and resize the supervisor root group on the display such that the Blinka logo is hidden
    blinky_logo_width = 16
    supervisor.reset_terminal(display.width + blinky_logo_width, display.height)
    repl_group.x = -blinky_logo_width
    repl_group.y = -5
    empty_group.append(repl_group)
    # That makes space for 21 characters on 8 lines on a 128x128px display

    return display
