import time

t_start = time.monotonic()  # To accurately measure the startup time

import alarm
import digitalio
import adafruit_bme280.advanced as adafruit_bme280
import board
import displayio
from adafruit_display_text import bitmap_label
import busio
from adafruit_lc709203f import LC709203F
import adafruit_il0373
import adafruit_am2320
from lib.tmf8821.adafruit_tmf8821 import TMF8821
from math import sqrt, floor, ceil

from adafruit_bitmap_font import bitmap_font

from utils.eink_constants import PaletteColor
from utils.graph_plot import GraphPlot
from utils.sleep_memory import Cyclic16BitTempBuffer, Cyclic16BitPercentageBuffer, SingleIntMemory
from utils.battery_widget import BatteryWidget, BLACK, DARK, BRIGHT, WHITE

BOOT_TIME = 0.0  # second
GRAPH_WIDTH = 161  # pixel
FLOOR_DISTANCE = 143  # millimeter

DEBUG = True
DEBUG_DELAY = 0.0


class Zoom:
    on = 1
    off = 2


class PlotType:
    growth = 1
    temp = 2


def read_board_environment(i2c_device: busio.I2C):
    bme280 = adafruit_bme280.Adafruit_BME280_I2C(i2c_device)
    bme280.mode = adafruit_bme280.MODE_FORCE
    bme280.iir_filter = adafruit_bme280.IIR_FILTER_DISABLE
    bme280.overscan_temperature = adafruit_bme280.OVERSCAN_X16
    bme280.overscan_humidity = adafruit_bme280.OVERSCAN_X4
    # Need to read twice: https://learn.adafruit.com/adafruit-bme280-humidity-barometric-pressure-temperature-sensor-breakout/f-a-q#faq-2958150
    dummy_read = bme280.temperature
    temperature = bme280.temperature
    humidity = bme280.humidity
    return temperature, humidity


def read_external_environment(i2c_device: busio.I2C):
    temperature = None
    humidity = None
    try:
        am2320 = adafruit_am2320.AM2320(i2c_device)
        time.sleep(0.1)
        temperature = am2320.temperature
        time.sleep(0.1)
        humidity = am2320.relative_humidity
    except ValueError:
        # This is an external sensor -- maybe it wasn't attached?
        pass
    return temperature, humidity


def read_distance(i2c_device: busio.I2C, floor: float, start: float, oversampling: int = 5):
    height = None
    growth_percentage = None
    mean_distance = None
    try:
        tof = TMF8821(i2c_device)
        tof.config.iterations = 3.5e6
        tof.config.period_ms = 1  # as small as possible for repeated measurements
        tof.config.spad_map = '3x3_normal_mode'
        tof.write_configuration()
        tof.start_measurements()
        all_distances = []
        for measurement_repetition in range(oversampling):
            measurement = tof.wait_for_measurement(timeout_ms=500)
            all_distances.extend(measurement.distances)
        tof.stop_measurements()
        mean_distance = sum(all_distances) / len(all_distances)
        if DEBUG:
            stddev = sqrt(sum([(d - mean_distance) ** 2 for d in all_distances]))
            print(f'Distance: {mean_distance:.2f} with std = {stddev}')
        if floor_height is None:
            # Floor height wasn't calibrated yet
            if DEBUG:
                print(f'Floor height not calibrated yet')
            raise Exception()
        height = floor_height - mean_distance
        if start_height is None:
            # Start height wasn't calibrated yet
            if DEBUG:
                print(f'Start height not calibrated yet')
            raise Exception()
        growth_percentage = height / start_height * 100
        if DEBUG:
            print(f'Floor: {floor_height}, Start: {start_height}, Height: {height}, Growth: {growth_percentage}')
    except Exception:
        # This is an external sensor -- maybe it wasn't attached?
        # Or either the floor or the start height wasn't calibrated
        pass
    return height, growth_percentage, mean_distance


def draw_texts(group, font_normal, font_bold, ext_temp, ext_humidity, board_temp, board_humidity, growth_percentage,
               peak_percentage, peak_hours, text_line1_y=7, text_line2_y=20):
    # Label for in: text
    group.append(bitmap_label.Label(font_normal, color=DARK, text='in:', x=2, y=text_line2_y))
    # Label for in temperature
    in_temp = '-' if ext_temp is None else f'{ext_temp:.1f}°C'
    group.append(bitmap_label.Label(font_bold, color=BLACK, text=in_temp, x=28, y=text_line2_y))
    # Label for in humidity
    if ext_humidity is not None:
        group.append(bitmap_label.Label(font_normal, color=BLACK, text=f'{ext_humidity:.0f}%rh', x=78, y=text_line2_y))
    # Label for out: text
    group.append(bitmap_label.Label(font_normal, color=DARK, text='out:', x=2, y=text_line1_y))
    # Label for board temperature
    group.append(bitmap_label.Label(font_bold, color=DARK, text=f'{board_temp:.1f}°C', x=28, y=text_line1_y))
    # Label for board humidity
    group.append(bitmap_label.Label(font_normal, color=DARK, text=f'{board_humidity:.0f}%rh', x=78, y=text_line1_y))
    # Label for growth: text
    group.append(bitmap_label.Label(font_normal, color=DARK, text='Growth:', x=140, y=text_line1_y))
    # Label for growth percentage
    growth = '-' if growth_percentage is None else f'{growth_percentage:.0f}%'
    group.append(bitmap_label.Label(font_bold, color=BLACK, text=growth, x=187, y=text_line1_y))
    if peak_percentage is not None:
        # Label for ago hour
        group.append(bitmap_label.Label(font_normal, color=BLACK, text=f'{peak_hours:.1f} h', x=140, y=text_line2_y))
        # Label for ago: text
        group.append(bitmap_label.Label(font_normal, color=DARK, text='ago:', x=167, y=text_line2_y))
        # Label for growth during peak
        group.append(bitmap_label.Label(font_bold, color=BLACK, text=f'{peak_percentage:.0f}%', x=194, y=text_line2_y))


try:
    displayio.release_displays()

    np_power = digitalio.DigitalInOut(board.NEOPIXEL_POWER)
    i2c_power = digitalio.DigitalInOut(board.I2C_POWER)

    # Disable power to NEOPIXEL
    np_power.switch_to_input()

    # Re-enable I2C from low power mode
    i2c_power.switch_to_input()
    default_state = i2c_power.value
    i2c_power.switch_to_output(value=not default_state)

    # Set up persistent memory
    plot_type_mem = SingleIntMemory(addr=0, default_value=PlotType.growth)
    zoom_mem = SingleIntMemory(addr=plot_type_mem.get_last_address(), default_value=Zoom.off)
    floor_height_mem = SingleIntMemory(addr=zoom_mem.get_last_address(), default_value=0)
    start_height_mem = SingleIntMemory(addr=floor_height_mem.get_last_address(), default_value=0)
    temp_mem = Cyclic16BitTempBuffer(addr=start_height_mem.get_last_address(), max_value_capacity=GRAPH_WIDTH)
    growth_mem = Cyclic16BitPercentageBuffer(addr=temp_mem.get_last_address(), max_value_capacity=GRAPH_WIDTH)

    plot_type = plot_type_mem()
    plot_zoomed = zoom_mem()
    floor_height = floor_height_mem()
    start_height = start_height_mem()

    if DEBUG:
        print('IO and memory initialized.')
        time.sleep(DEBUG_DELAY)

    # Initialize I2C
    i2c = busio.I2C(board.SCL, board.SDA, frequency=125000)

    # Read outside temperature and humidity from BME280 sensor
    board_temp, board_humidity = read_board_environment(i2c)
    temp_mem.add_value(board_temp)

    if DEBUG:
        print("BME280 read.")
        time.sleep(DEBUG_DELAY)

    # Read inside temperature and humidity from AM2320 sensor
    ext_temp, ext_humidity = read_external_environment(i2c)

    if DEBUG:
        print("AM2320 read.")
        time.sleep(DEBUG_DELAY)

    # Read time-of-flight distance from TMF8821 sensor
    height, growth_percentage, distance = read_distance(i2c, floor_height, start_height)

    # Read charge percentage from battery monitor
    battery_percentage = LC709203F(i2c).cell_percent

    if DEBUG:
        print("battery monitor initialized.")
        time.sleep(DEBUG_DELAY)

    # Handle buttons: left button toggles temp/growth and middle button toggles zoom/full history
    wake = alarm.wake_alarm
    if wake is None:
        wake_reason = 'reset'
        if DEBUG:
            print('Wakeup: Reset')
    elif isinstance(wake, alarm.time.TimeAlarm):
        wake_reason = 'timeout'
        if DEBUG:
            print(f'Wakeup: timeout')
    elif isinstance(wake, alarm.pin.PinAlarm):
        if DEBUG:
            print(f'Wakeup: Pin {wake.pin} = {wake.value}')
        if wake.pin == board.D11:
            # Left button: toggle growth or temp
            wake_reason = 'left'
        elif wake.pin == board.D12:
            # Middle button: toggle zoom
            wake_reason = 'middle'

    # Initialize e-Ink display
    with busio.SPI(board.SCK, board.MOSI) as spi:
        epd_cs = board.D9
        epd_dc = board.D10
        display_bus = displayio.FourWire(spi, command=epd_dc, chip_select=epd_cs, baudrate=1000000)
        time.sleep(0.1)
        display = adafruit_il0373.IL0373(display_bus, width=296, height=128, rotation=270, black_bits_inverted=False,
                                         color_bits_inverted=False, grayscale=True, refresh_time=1, border=None)

        if DEBUG:
            print("display initialized.")
            time.sleep(DEBUG_DELAY)

        # Load fonts
        tick_font = bitmap_font.load_font('fonts/00Starmap-11-11.bdf')
        tahoma_font = bitmap_font.load_font('fonts/Tahoma_12.bdf')
        tahoma_bold_font = bitmap_font.load_font('fonts/Tahoma-Bold_12.bdf')

        # Main display group
        g = displayio.Group()

        # Load background bitmap
        f_bg = open('background.bmp' if plot_zoomed == Zoom.off else 'background_zoom.bmp', 'rb')
        pic = displayio.OnDiskBitmap(f_bg)
        t = displayio.TileGrid(pic, pixel_shader=pic.pixel_shader)
        g.append(t)

        if DEBUG:
            print('Display background drawn.')
            time.sleep(DEBUG_DELAY)

        # TODO: calculate peak
        peak_percentage = None
        peak_hours = None

        draw_texts(g, tahoma_font, tahoma_bold_font, ext_temp, ext_humidity, board_temp, board_humidity,
                   growth_percentage, peak_percentage, peak_hours)

        if DEBUG:
            print("Labels drawn.")
            time.sleep(DEBUG_DELAY)

        battery_symbol = BatteryWidget(x=250, y=4, width=10, height=19, upper_part_height=2, upper_part_width=4,
                                       background_color=PaletteColor.light_gray, fill_color=PaletteColor.black,
                                       exclamation_mark_threshold=0.038)
        battery_symbol.draw(battery_percentage / 100)
        g.append(battery_symbol)
        g.append(bitmap_label.Label(tahoma_font, color=DARK, text=f'{battery_percentage:.0f}%', x=263, y=13))

        if DEBUG:
            print("Battery symbol drawn.")
            time.sleep(DEBUG_DELAY)
            print(f'Startup time just before graph: {time.monotonic() - t_start:.2f}s')

        # Check if a button was held the whole time:
        if wake_reason == 'left':
            with digitalio.DigitalInOut(board.D11) as left_button:
                left_button.switch_to_input(digitalio.Pull.UP)
                left_button_pressed = not left_button.value
            if left_button_pressed:
                # Left button pressed the whole time:
                if distance is not None:
                    if DEBUG:
                        print(f'Floor height was reset: from {floor_height}mm to {round(distance)}mm')
                    floor_height = floor_height_mem(new_value=round(distance))
                    g.append(bitmap_label.Label(tahoma_bold_font, color=BLACK, text=f'Floor calib {round(distance)}mm',
                                                x=95, y=56, background_color=WHITE))
                    growth_percentage = None  # Floor was reset --> until recalibration of normal height, don't update growth
            else:
                # Left button pressed and released
                if DEBUG:
                    print(f'Switching plot: {plot_type} -> {3 - plot_type}')
                plot_type = plot_type_mem(3 - plot_type)
        elif wake_reason == 'middle':
            with digitalio.DigitalInOut(board.D12) as middle_button:
                middle_button.switch_to_input(digitalio.Pull.UP)
                middle_button_pressed = not middle_button.value
            if middle_button_pressed:
                # Middle button pressed the whole time:
                if height is not None:
                    if DEBUG:
                        print(f'Normal height was reset: from {start_height}mm to {floor(height)}mm')
                    start_height = start_height_mem(new_value=floor(height))
                    g.append(bitmap_label.Label(tahoma_bold_font, color=BLACK, text=f'Height calib {floor(height)}mm',
                                                x=90, y=75, background_color=WHITE))
                    if floor_height is not None:
                        # Right after calibration is complete, the first reading must be 100%
                        growth_percentage = 100.0
            else:
                # Middle button pressed and released
                if DEBUG:
                    print(f'Switching zoom: {plot_zoomed} -> {3 - plot_zoomed}')
                plot_zoomed = zoom_mem(3 - plot_zoomed)
        
        # Add current growth percentage to buffer
        if floor_height is not None and start_height is not None and growth_percentage is not None:
            growth_mem.add_value(growth_percentage)

        # Add the graph plot
        plot = GraphPlot(
            width=296, height=128, origin=(28, 116), top_right=(288, 35), font=tick_font, line_color=PaletteColor.black,
            yticks_color=PaletteColor.dark_gray, font_color=PaletteColor.dark_gray, line_width=1,
            background_color=PaletteColor.transparent, ygrid_color=PaletteColor.light_gray, font_size=(5, 7),
            alignment='right')

        if plot_type == PlotType.temp:
            plot_amount = temp_mem.current_size if plot_zoomed == Zoom.off else ceil(temp_mem.current_size / 2.0)
            # temp_mem.debug_print()
            value_array = temp_mem.read_array(amount=plot_amount)
        else:
            plot_amount = growth_mem.current_size if plot_zoomed == Zoom.off else ceil(growth_mem.current_size / 2.0)
            # growth_mem.debug_print()
            value_array = growth_mem.read_array(amount=plot_amount)
        if value_array:
            # print(f'Value array: {",".join(map(str, value_array))}')
            plot.plot_graph(value_array, zoomed=plot_zoomed == Zoom.on)
        g.append(plot)

        if floor_height is None:
            g.append(bitmap_label.Label(tahoma_bold_font, color=BLACK, text=f'Floor not calibrated',
                                        x=95, y=56, background_color=WHITE))
        if start_height is None:
            g.append(bitmap_label.Label(tahoma_bold_font, color=BLACK, text=f'Height not calibrated',
                                        x=90, y=75, background_color=WHITE))

        if DEBUG:
            print("Plot drawn.")
            time.sleep(DEBUG_DELAY)

        display.show(g)
        display.refresh()

        if DEBUG:
            print("Display refreshed.")
            time.sleep(DEBUG_DELAY)

        # Prepare for low power deep sleep
        displayio.release_displays()

    f_bg.close()

    # Disable power to I2C bus
    i2c_power.switch_to_input()

    if DEBUG:
        print("Setting up deep sleep.")
        time.sleep(DEBUG_DELAY)

    # If a button was pressed, we assume that the interruption in average occurs after 1.5 min
    # --> wait for 4.5 min to compensate for the early interrupt (we aim at a constant sampling frequency of 3 min)
    next_alarm = 3 * 60 if wake_reason not in ['left', 'middle'] else 4.5 * 60
    timeout_alarm = alarm.time.TimeAlarm(monotonic_time=t_start - BOOT_TIME + 3 * 60)
    left_alarm = alarm.pin.PinAlarm(pin=board.D11, value=False, pull=True)
    middle_alarm = alarm.pin.PinAlarm(pin=board.D12, value=False, pull=True)
    alarm.exit_and_deep_sleep_until_alarms(timeout_alarm, left_alarm, middle_alarm)
    # We will never get *here* -> timeout will force a restart and execute code from the top
except KeyError as e:
    print(e)
    pass
