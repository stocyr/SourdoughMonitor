import time

t_start = time.monotonic()  # To accurately measure the startup time
import digitalio
import board

i2c_power = digitalio.DigitalInOut(board.I2C_POWER)
i2c_power.switch_to_input()

# ===================== CONSTANTS =======================
BOOT_TIME = 1.3  # second
GRAPH_WIDTH = 261  # pixel
DEBUG = True
DEBUG_DELAY = 0.0
# =======================================================

from math import sqrt, floor, ceil
import alarm
import busio
import neopixel
import adafruit_bme280.advanced as adafruit_bme280
import displayio
from adafruit_display_text import bitmap_label
from adafruit_lc709203f import LC709203F
import adafruit_il0373
import adafruit_am2320
from lib.tmf8821.adafruit_tmf8821 import TMF8821
from adafruit_bitmap_font import bitmap_font

# Read buttons
if DEBUG:
    print(f'Startup time just before checking the buttons: {BOOT_TIME + time.monotonic() - t_start:.2f}s')
with digitalio.DigitalInOut(board.D11) as left_button:
    left_button.switch_to_input(digitalio.Pull.UP)
    left_button_pressed = not left_button.value
    left_button.pull = None
with digitalio.DigitalInOut(board.D12) as middle_button:
    middle_button.switch_to_input(digitalio.Pull.UP)
    middle_button_pressed = not middle_button.value
    middle_button.pull = None
with digitalio.DigitalInOut(board.D13) as right_button:
    right_button.switch_to_input(digitalio.Pull.UP)
    right_button_pressed = not right_button.value
    right_button.pull = None

rgb_led = neopixel.NeoPixel(board.NEOPIXEL, 1)
rgb_led.fill((0, 0, 255))

# Power up i2c devices
default_state = i2c_power.value
i2c_power.switch_to_output(not default_state)

from utils.eink_constants import PaletteColor
from utils.graph_plot import GraphPlot
from utils.sleep_memory import CyclicBuffer, Cyclic16BitTempBuffer, Cyclic16BitPercentageBuffer, SingleIntMemory
from utils.battery_widget import BatteryWidget, BLACK, DARK, WHITE

rgb_led.deinit()


# ===================== METHODS =======================

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
    # Need to read twice: https://learn.adafruit.com/adafruit-bme280-humidity-barometric-pressure-temperature-
    # sensor-breakout/f-a-q#faq-2958150
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
        if DEBUG:
            print(f'External sensor not readable!')
    return temperature, humidity


def read_distance(i2c_device: busio.I2C, oversampling: int = 5) -> float:
    mean_distance = None
    try:
        tof = TMF8821(i2c_device)
        tof.config.iterations = 3.5e6
        tof.config.period_ms = 1  # as small as possible for repeated measurements
        tof.config.spad_map = '3x3_normal_mode'
        tof.config.spread_spectrum_factor = 3
        tof.active_range = 'short'
        tof.write_configuration()
        tof.load_factory_calibration(calib_folder='calibration')
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
        return mean_distance
    except Exception:
        return None


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


def log_data_to_sd_card(floor_calib: int, start_calib: int, temp_buffer: CyclicBuffer, growth_buffer: CyclicBuffer):
    import os
    import sdcardio
    import storage
    try:
        with busio.SPI(board.SCK, board.MOSI, board.MISO) as spi:
            sd_cd = board.D5
            sd = sdcardio.SDCard(spi, sd_cd)
            vfs = storage.VfsFat(sd)
            storage.mount(vfs, '/sd')

            files = os.listdir('/sd')
            data_files = [f for f in files if f.startswith('data_') and f.endswith('.csv')]
            if data_files:
                next_number = int(sorted(data_files, reverse=True)[0][5:8]) + 1
            else:
                next_number = 0

            # Read both buffers into arrays
            growth_array = growth_buffer.read_array()
            temp_array = temp_buffer.read_array()

            with open(f'/sd/data_{next_number:03d}.csv', 'w') as file:
                file.write(f'# Floor distance: {floor_calib}mm, start height: {start_calib}mm\n')
                file.write('growth,temp\n')
                max_rows = max(len(growth_array), len(temp_array))
                for i in range(max_rows):
                    i_growth = i - (max_rows - len(growth_array))
                    i_temp = i - (max_rows - len(temp_array))
                    if i_growth >= 0:
                        file.write(f'{growth_array[i_growth]:.2f},')
                    else:
                        file.write(',')
                    if i_temp >= 0:
                        file.write(f'{temp_array[i_temp]:.2f}')
                    file.write('\n')
            # Close SD card connection and safely unmount
            sd.sync()
            storage.umount(vfs)
    except Exception as e:
        if DEBUG:
            print(f'Couldn\'t write to SD card: {e}')


# ===================== MAIN CODE =======================

try:
    displayio.release_displays()

    message_lines = {'am2320': ('', False), 'tmf8821': ('', False), 'height_calibration': ('', False)}

    # Determine wakeup reason
    wake = alarm.wake_alarm
    wake_reason = 'unknown'
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
            wake_reason = 'left'
        elif wake.pin == board.D12:
            wake_reason = 'middle'

    # Set up persistent memory
    plot_type_mem = SingleIntMemory(addr=0, default_value=PlotType.growth)
    zoom_mem = SingleIntMemory(addr=plot_type_mem.get_last_address(), default_value=Zoom.on)
    floor_distance_mem = SingleIntMemory(addr=zoom_mem.get_last_address(), default_value=0)
    start_height_mem = SingleIntMemory(addr=floor_distance_mem.get_last_address(), default_value=0)
    temp_mem = Cyclic16BitTempBuffer(addr=start_height_mem.get_last_address(), max_value_capacity=GRAPH_WIDTH)
    growth_mem = Cyclic16BitPercentageBuffer(addr=temp_mem.get_last_address(), max_value_capacity=GRAPH_WIDTH)

    plot_type = plot_type_mem.value
    plot_zoomed = zoom_mem.value
    floor_distance = floor_distance_mem.value
    start_height = start_height_mem.value

    # Mockup mode
    if wake_reason == 'reset' and right_button_pressed:
        # Right button pressed during reset startup: mockup mode
        # TODO: change to empty the plots --> at least the height...
        temp_mem.fill_randomly(19.0, 29.0)
        growth_mem.fill_randomly(100.0, 150.0)
        if DEBUG:
            print('Filled both buffers with mock values')
    if DEBUG:
        print(f'Buffers: {growth_mem.current_size}, {temp_mem.current_size}')

    if DEBUG:
        print('IO and memory initialized.')
        time.sleep(DEBUG_DELAY)

    # Initialize I2C
    if DEBUG:
        print(f'Wake time until i2c init: {BOOT_TIME + time.monotonic() - t_start:.2}s')
    i2c = busio.I2C(board.SCL, board.SDA, frequency=125000)

    # Read outside temperature and humidity from BME280 sensor
    board_temp, board_humidity = read_board_environment(i2c)

    if DEBUG:
        print("BME280 read.")
        time.sleep(DEBUG_DELAY)

    # Read inside temperature and humidity from AM2320 sensor
    # TODO: let the exception pass through, then print a message if sensor problem
    ext_temp, ext_humidity = read_external_environment(i2c)
    if ext_temp is not None:
        temp_mem.add_value(ext_temp)
    else:
        message_lines['am2320'] = (' Cannot read from AM2320 ', True)

    if DEBUG:
        print("AM2320 read.")
        time.sleep(DEBUG_DELAY)

    # Read time-of-flight distance from TMF8821 sensor
    current_distance = read_distance(i2c)

    # Handle distance and calibrations
    growth_percentage = None
    dought_height = None
    pausing = False
    if current_distance is None:
        if DEBUG:
            print(f'Couldn\'t read from distance sensor!')
        message_lines['tmf8821'] = (' Cannot read from TMF8821 ', True)
    else:
        # Distance measurement received
        if current_distance <= 11:
            # Object directly on the sensor --> lid sits on a surface
            pausing = True
            if DEBUG:
                print(f'Lid sits on a surface')
            message_lines['tmf8821'] = ('ToF sensor blocked, pausing', False)
        else:
            # Valid distance measurement
            if floor_distance is None:
                # Floor height wasn't calibrated yet
                if DEBUG:
                    print('Floor height not calibrated yet')
                message_lines['tmf8821'] = (' Floor distance not calibrated ', True)
            else:
                # Floor height was calibrated
                dought_height = floor_distance - current_distance
                if start_height is None:
                    # Start height wasn't calibrated yet
                    if DEBUG:
                        print(f'Start height not calibrated yet')
                    message_lines['height_calibration'] = (' Start height not calibrated ', True)
                else:
                    # Start height calibrated
                    growth_percentage = dought_height / start_height * 100
                    if DEBUG:
                        print(f'Floor: {floor_distance / 10:.1f}cm, Start height: {start_height / 10:.1f}cm, ', end='')
                        print(f'Current height: {dought_height / 10:.1f}cm, Growth: {growth_percentage:.2f}%')

    # Read charge percentage from battery monitor
    battery_percentage = LC709203F(i2c).cell_percent
    if DEBUG:
        print(f'Battery percentage: {battery_percentage}')

    # Disable power to I2C bus
    i2c_power.switch_to_input()

    # Button press logic
    if left_button_pressed and middle_button_pressed:
        # Both buttons pressed --> Store log
        log_data_to_sd_card(floor_distance, start_height, temp_mem, growth_mem)
        if DEBUG:
            print(f'Logged data to SD card')
        if message_lines['height_calibration'][0] == '':
            message_lines['height_calibration'] = ('Logged data to SD card', False)
    elif wake_reason == 'left':
        if left_button_pressed:
            # Left button pressed --> calibrate floor
            if current_distance is not None and not pausing:
                distance_rounded = round(current_distance)
                if DEBUG:
                    print(f'Floor distance was reset to {distance_rounded / 10:.1f}cm')
                floor_distance_mem.value = distance_rounded
                floor_distance = distance_rounded
                message_lines['tmf8821'] = (f'Floor calib {distance_rounded / 10:.1f}cm', False)
                # Floor was reset, so until recalibration of normal height, don't update growth
                growth_percentage = None
                # Also reset history of growths
                growth_mem.make_empty()
        else:
            # Left button clicked --> toggle plot type
            new_plot_type = 3 - plot_type
            if DEBUG:
                print(f'Switching plot: {plot_type} -> {new_plot_type}')
            plot_type_mem.value = new_plot_type
            plot_type = new_plot_type
    elif wake_reason == 'middle':
        if middle_button_pressed:
            # Middle button pressed --> calibrate height
            if dought_height is not None:
                start_height_floored = int(floor(dought_height))
                if DEBUG:
                    print(f'Start height was reset to {dought_height / 10:.1f}cm')
                start_height_mem.value = start_height_floored
                start_height = start_height_floored
                message_lines['height_calibration'] = (f'Start height calib {start_height_floored / 10:.1f}cm', False)
                if floor_distance is not None:
                    # Right after calibration is complete, the first reading must be 100%
                    growth_percentage = 100.0
                    # Also clear growth mem
                    growth_mem.make_empty()
        else:
            # Middle button clicked --> toggle plot zoom
            new_plot_zoomed = 3 - plot_zoomed
            if DEBUG:
                print(f'Switching zoom: {plot_zoomed} -> {new_plot_zoomed}')
            zoom_mem.value = new_plot_zoomed
            plot_zoomed = new_plot_zoomed

    if DEBUG:
        print("battery monitor initialized.")
        time.sleep(DEBUG_DELAY)

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

        # Load fonts and glyphs --> speeds up label rendering
        # https://learn.adafruit.com/custom-fonts-for-pyportal-circuitpython-display/bitmap_font-library
        tick_font = bitmap_font.load_font('fonts/00Starmap-11-11.pcf')
        tahoma_font = bitmap_font.load_font('fonts/Tahoma_12.pcf')
        tahoma_bold_font = bitmap_font.load_font('fonts/Tahoma-Bold_12.pcf')
        tahoma_font.load_glyphs(b'1234567890-. ')
        tick_font.load_glyphs(b' %+,-.1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ')
        tahoma_bold_font.load_glyphs(b' %+,-.1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ')

        # Main display group
        g = displayio.Group()

        # Load background bitmap
        f_bg = open('background_zoom.bmp' if plot_zoomed == Zoom.on else 'background.bmp', 'rb')
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
        if battery_symbol.critical_battery and message_lines['am2320'][0] == '':
            message_lines['am2320'] = (' Low battery ', True)
        g.append(battery_symbol)
        g.append(bitmap_label.Label(tahoma_font, color=DARK, text=f'{battery_percentage:.0f}%', x=263, y=13))

        if DEBUG:
            print("Battery symbol drawn.")
            time.sleep(DEBUG_DELAY)

        # Add current growth percentage to buffer
        if floor_distance is not None and start_height is not None and growth_percentage is not None and not pausing:
            # TODO: always add value if we also add values to the temperature. but consider NaN in these cases
            # - leave nan empty in plot -> if next value is NaN or current value is NaN, skip line
            # - don't consider NaN in min/max calculation -> use either numpy or our own min/max implementation
            growth_mem.add_value(growth_percentage)

        # Add the graph plot
        plot = GraphPlot(
            width=296, height=128, origin=(28, 116), top_right=(288, 35), font=tick_font, line_color=PaletteColor.black,
            yticks_color=PaletteColor.dark_gray, font_color=PaletteColor.dark_gray, line_width=1,
            background_color=PaletteColor.transparent, ygrid_color=PaletteColor.light_gray, font_size=(5, 7),
            alignment='right')

        plot_mem: CyclicBuffer = temp_mem if plot_type == PlotType.temp else growth_mem
        if plot_zoomed == Zoom.on:
            plot_amount = min(plot_mem.current_size, ceil(GRAPH_WIDTH / 2.0))
        else:
            plot_amount = plot_mem.current_size

        value_array = plot_mem.read_array(amount=plot_amount)

        if value_array:
            # print(f'Value array: {",".join(map(str, value_array))}')
            plot.plot_graph(value_array, zoomed=plot_zoomed == Zoom.on)
        g.append(plot)

        # Write message lines
        for key, y_pos in zip(['am2320', 'tmf8821', 'height_calibration'], [50, 70, 90]):
            message, emphasize = message_lines[key]
            if message != '':
                color_fg, color_bg = (WHITE, BLACK) if emphasize else (BLACK, WHITE)
                g.append(bitmap_label.Label(tahoma_bold_font, color=color_fg, text=message, x=75, y=y_pos,
                                            background_color=color_bg))

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
finally:
    # except BufferError as e:
    # print(e)
    pass
