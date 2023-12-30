'''Copyright (c) 2022-2024, Cyril Stoller'''
import time

t_start = time.monotonic()  # To accurately measure the startup time
import digitalio
import board

i2c_power = digitalio.DigitalInOut(board.I2C_POWER)
i2c_power.switch_to_input()

# ===================== CONSTANTS =======================
BOOT_TIME = 1.3  # second
GRAPH_WIDTH = 261  # pixel
DEBUG = False
DEBUG_DELAY = 0.0
FRIDGE_SLEEP_TIME_FACTOR = 3
FRIDGE_MAX_TEMP = 10
INVERTED = False
INTERVAL_MINUTES = 4
TELEMETRY = True
INFLUXDB_MEASUREMENT = "rise"
DEVICE_NAME = "ESP32-S2"
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
from adafruit_bitmap_font import bitmap_font
import ipaddress
import wifi
import socketpool
import ssl
import adafruit_requests

from lib.tmf8821.adafruit_tmf8821 import TMF8821
from metric_telemetry.secrets import WIFI_AUTH, INFLUXDB_URL, INFLUXDB_API_TOKEN

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
from utils.algorithm import peak_detect

rgb_led.deinit()


# ===================== METHODS =======================

class Zoom:
    on = 1
    off = 2


class PlotType:
    growth = 1
    temp = 2


def read_latest_data_file() -> list:
    import os
    import sdcardio
    import storage
    array = []
    #    try:
    with busio.SPI(board.SCK, board.MOSI, board.MISO) as spi:
        sd_cd = board.D5
        sd = sdcardio.SDCard(spi, sd_cd)
        vfs = storage.VfsFat(sd)
        storage.mount(vfs, '/sd', readonly=True)

        files = os.listdir('/sd')
        data_files = [f for f in files if f.startswith('data_') and f.endswith('.csv')]
        if data_files:
            latest_number = int(sorted(data_files, reverse=True)[0][5:8])
            # Read growth values into arrays
            with open(f'/sd/data_{latest_number:03d}.csv', 'r') as file:
                for line in file.readlines():
                    growth, temp = line.split(',')
                    try:
                        array.append(float(growth))
                    except Exception:
                        pass
        # Close SD card connection
        storage.umount(vfs)
    #    except Exception:
    #        pass
    return array


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


def read_external_environment(i2c_device: busio.I2C, retry_temp=3, temp_invalid=0):
    temperature = None
    humidity = None
    while (temperature is None or temperature == temp_invalid) and retry_temp > 0:
        try:
            am2320 = adafruit_am2320.AM2320(i2c_device)
            time.sleep(0.3)
            temperature = am2320.temperature
            time.sleep(0.2)
            humidity = am2320.relative_humidity
        except (ValueError, OSError):
            # This is an external sensor -- maybe it wasn't attached?
            if DEBUG:
                print(f'External sensor not readable!')
        retry_temp -= 1
    return temperature, humidity


def read_distance(i2c_device: busio.I2C, oversampling: int = 5) -> tuple[float, float]:
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
        stddev = sqrt(sum([(d - mean_distance) ** 2 for d in all_distances]))
        if DEBUG:
            print(f'Distance: {mean_distance:.2f} with std = {stddev}')
        return mean_distance, stddev
    except Exception:
        return None, None


def draw_texts(group, font_normal, font_bold, ext_temp, ext_humidity, board_temp, board_humidity, growth_percentage,
               peak_percentage, peak_hours, text_line1_y=7, text_line2_y=20):
    # Label for in: text
    group.append(bitmap_label.Label(font_normal, color=DARK, text='in:', x=2, y=text_line2_y))
    # Label for in temperature
    in_temp = '-' if ext_temp is None else f'{ext_temp:.1f}°C'
    group.append(bitmap_label.Label(font_bold, color=BLACK, text=in_temp, x=28, y=text_line2_y))
    # Label for in humidity
    # if ext_humidity is not None:
    #    group.append(bitmap_label.Label(font_normal, color=BLACK, text=f'{ext_humidity:.0f}%rh', x=78, y=text_line2_y))
    # Label for out: text
    group.append(bitmap_label.Label(font_normal, color=DARK, text='out:', x=2, y=text_line1_y))
    # Label for board temperature
    group.append(bitmap_label.Label(font_bold, color=DARK, text=f'{board_temp:.1f}°C', x=28, y=text_line1_y))
    # Label for board humidity
    # group.append(bitmap_label.Label(font_normal, color=DARK, text=f'{board_humidity:.0f}%rh', x=78, y=text_line1_y))
    if growth_percentage is not None:
        # Label for growth: text
        group.append(bitmap_label.Label(font_normal, color=DARK, text='Growth:', x=140, y=text_line1_y))
        # Label for growth percentage
        group.append(bitmap_label.Label(font_bold, color=BLACK, text=f'{growth_percentage:.0f}%', x=187,
                                        y=text_line1_y))
    if peak_percentage is not None:
        # Label for ago hour
        group.append(bitmap_label.Label(font_normal, color=BLACK, text=f'{peak_hours:.1f}h', x=140, y=text_line2_y))
        x_off = 0 if len(f'{peak_hours:.1f}h') <= 4 else 6
        # Label for ago: text
        group.append(bitmap_label.Label(font_normal, color=DARK, text='ago:', x=167 + x_off, y=text_line2_y))
        # Label for growth during peak
        group.append(bitmap_label.Label(font_bold, color=BLACK, text=f'{peak_percentage:.0f}%', x=194 + x_off,
                                        y=text_line2_y))


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


def log_exception_to_sd_card(exc):
    import os
    import traceback
    import sdcardio
    import storage
    exc_string = traceback.format_exception(type(exc), exc, exc.__traceback__)
    try:
        with busio.SPI(board.SCK, board.MOSI, board.MISO) as spi:
            sd_cd = board.D5
            sd = sdcardio.SDCard(spi, sd_cd)
            vfs = storage.VfsFat(sd)
            storage.mount(vfs, '/sd')

            with open(f'/sd/exception_traceback.txt', 'w') as file:
                file.write(exc_string)
            # Close SD card connection and safely unmount
            sd.sync()
            storage.umount(vfs)
    except:
        pass
    return exc_string


def connect_to_wifi():
    global wifi_connectivity, wifi_chan_mem
    # Construct indices of Wi-Fi configurations such that the previously working one is at the front
    if len(WIFI_AUTH) > wifi_idx_mem.value:
        wifi_trial_indices = [wifi_idx_mem.value] + [i for i in range(len(WIFI_AUTH)) if i != wifi_idx_mem.value]
    else:
        wifi_trial_indices = list(range(len(WIFI_AUTH)))
    for ind, (ssid, passwd) in [(i, WIFI_AUTH[i]) for i in wifi_trial_indices]:
        try:
            wifi.radio.connect(ssid=ssid, password=passwd, channel=wifi_chan_mem.value)
            if wifi.radio.ap_info is not None:
                # Wi-Fi successfully connected!
                wifi_connectivity = wifi.radio.ap_info.rssi
                # Potentially update working Wi-Fi configuration to persistent memory
                wifi_chan_mem.value = wifi.radio.ap_info.channel
                wifi_idx_mem.value = ind
                break
        except ConnectionError as e:
            # Cannot connect
            if DEBUG:
                print(f'Cannot connect to the Wi-Fi {ssid} with pw "{passwd}": {e}')
    else:
        # Didn't find any working Wi-Fi key pair
        if DEBUG:
            print(f'None of the {len(WIFI_AUTH)} Wi-Fi configuration(s) is working!')


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
    wifi_idx_mem = SingleIntMemory(addr=growth_mem.get_last_address(), default_value=0, invalid_value=-1, size=1)
    wifi_chan_mem = SingleIntMemory(addr=wifi_idx_mem.get_last_address(), default_value=0, invalid_value=-1, size=1)

    plot_type = plot_type_mem.value
    plot_zoomed = zoom_mem.value
    floor_distance = floor_distance_mem.value
    start_height = start_height_mem.value

    # Look up if a floor calibration file is present
    if floor_distance is None:
        try:
            with open('calibration/floor.txt', 'r') as f:
                floor_distance = int(float(f.read()))
                floor_distance_mem.value = floor_distance
                if DEBUG:
                    print(f'Floor distance was loaded from file to {floor_distance / 10:.1f}cm')
                message_lines['tmf8821'] = (f'Floor distance from file {floor_distance / 10:.1f}cm ', False)
        except Exception:
            pass

    # Mockup mode
    if wake_reason == 'reset' and right_button_pressed:
        # Right button pressed during reset startup: mockup mode
        growth_array = read_latest_data_file()
        if growth_array:
            # Try to find the latest file on the SD card and replay it
            growth_mem.make_empty()
            for val in growth_array:
                growth_mem.add_value(val)
            if DEBUG:
                print(f'Filled growth buffer with {len(growth_array)} values from SD card')
            message_lines['tmf8821'] = (f'{len(growth_array)} growth values loaded from SD card', False)
        else:
            # Otherwise, fill randomly
            temp_mem.fill_randomly(19.0, 29.0)
            growth_mem.fill_randomly(100.0, 150.0)
            if DEBUG:
                print('Filled both buffers with mock values')
            message_lines['tmf8821'] = (f'Growth and temp randomized', False)
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
    ext_temp, ext_humidity = read_external_environment(i2c)
    if ext_temp is not None:
        temp_mem.add_value(ext_temp)
    else:
        message_lines['am2320'] = (' Cannot read from AM2320 ', True)

    if DEBUG:
        print("AM2320 read.")
        time.sleep(DEBUG_DELAY)

    # Read time-of-flight distance from TMF8821 sensor
    current_distance, distance_stddev = read_distance(i2c)

    # Handle distance and calibrations
    growth_percentage = None
    dough_height = None
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
            # message_lines['height_calibration'] = ('Distance sensor blocked, pausing', False)
        else:
            # Valid distance measurement
            if floor_distance is None:
                # Floor height wasn't calibrated yet
                if DEBUG:
                    print('Floor height not calibrated yet')
                message_lines['tmf8821'] = (' Floor distance not calibrated ', True)
            else:
                # Floor height was calibrated
                dough_height = floor_distance - current_distance
                if start_height is None:
                    # Start height wasn't calibrated yet
                    if DEBUG:
                        print(f'Start height not calibrated yet')
                    message_lines['height_calibration'] = (' Start height not calibrated ', True)
                else:
                    # Start height calibrated
                    growth_percentage = dough_height / start_height * 100
                    if DEBUG:
                        print(f'Floor: {floor_distance / 10:.1f}cm, Start height: {start_height / 10:.1f}cm, ', end='')
                        print(f'Current height: {dough_height / 10:.1f}cm, Growth: {growth_percentage:.2f}%')

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
            if dough_height is not None:
                if dough_height > 0:
                    start_height_floored = int(floor(dough_height))
                    if DEBUG:
                        print(f'Start height was reset to {dough_height / 10:.1f}cm')
                    start_height_mem.value = start_height_floored
                    start_height = start_height_floored
                    message_lines['height_calibration'] = (
                        f'Start height calib {start_height_floored / 10:.1f}cm', False)
                    if floor_distance is not None:
                        # Right after calibration is complete, the first reading must be 100%
                        growth_percentage = 100.0
                        # Also clear growth mem
                        growth_mem.make_empty()
                else:
                    if DEBUG:
                        print(f'Start height {dough_height / 10:.1f}cm is lower than floor height {floor_distance}mm')
                    message_lines['height_calibration'] = ('Start height lower than floor height', True)
        else:
            # Middle button clicked --> toggle plot zoom
            new_plot_zoomed = 3 - plot_zoomed
            if DEBUG:
                print(f'Switching zoom: {plot_zoomed} -> {new_plot_zoomed}')
            zoom_mem.value = new_plot_zoomed
            plot_zoomed = new_plot_zoomed

    # Add current growth percentage to buffer
    if growth_percentage is not None:
        growth_mem.add_value(growth_percentage)
    # Perform peak search
    growth_array = growth_mem.read_array()
    peak_ind = peak_detect(growth_array, threshold=1.0, window_size=7)
    peak_pos_in_history = None
    peak_percentage = None
    peak_hours = None
    if peak_ind is not None:
        peak_pos_in_history = len(growth_array) - peak_ind - 1
        peak_percentage = growth_array[peak_ind]
        peak_hours = peak_pos_in_history * INTERVAL_MINUTES / 60
    if DEBUG:
        print(f'peak percentage: {peak_percentage}, peak hours: {peak_hours}, peak ind {peak_ind}')

    # Try to connect to the internet and send telemetry metrics
    wifi_connectivity = "None"
    telemetry_success = False
    if TELEMETRY:
        wifi.radio.enabled = True
        connect_to_wifi()

        if wifi_connectivity is not None:
            # Prepare requests library
            pool = socketpool.SocketPool(wifi.radio)
            with open('all_certs.pem', 'r') as f:
                CA_STRING = f.read()  # Use custom CA chain for InfluxDB TLS access
            context = ssl.create_default_context()
            context.load_verify_locations(cadata=CA_STRING)
            request = adafruit_requests.Session(pool, context)
            HEADERS = {
                "Authorization": f"Token {INFLUXDB_API_TOKEN}",
                "precision": "s"
            }
            influxdb_row = f"{INFLUXDB_MEASUREMENT},device={DEVICE_NAME} " + \
                           f"height={growth_percentage:.2f}," if growth_percentage is not None else "" + \
                           f"height_std={distance_stddev:.2f}," if distance_stddev is not None else "" + \
                           f"floor_calib={floor_distance:.2f}," if floor_distance is not None else "" + \
                           f"start_calib={start_height:.2f}," if start_height is not None else "" \
                           f"temp_in={ext_temp:.2f}," if ext_temp is not None else "" + \
                           f"temp_out={board_temp:.2f}," + \
                           f"hum_in={ext_humidity:.2f}," if ext_humidity is not None else "" + \
                           f"hum_out={board_humidity:.2f}," if board_humidity is not None else "" + \
                           f"wifi_rssi={wifi_connectivity:d}," + \
                           f"wake_reason=\"{wake_reason}\"," + \
                           f"battery_level={battery_percentage:.2f}"

            if DEBUG:
                print(f"InfluxDB Row: {influxdb_row}")
                time.sleep(DEBUG_DELAY)

            try:
                response = request.post(INFLUXDB_URL, headers=HEADERS, data=influxdb_row)
                if response.status_code == 204:
                    telemetry_success = True
                    if DEBUG:
                        print("Data sent to InfluxDB successfully!")
                else:
                    raise Exception(f"InfluxDB didn't return status 204: {response.text}")
                response.close()
            except Exception as e:
                exc_string = log_exception_to_sd_card(e)
                if DEBUG:
                    print(f"InfluxDB problem: {exc_string}")

        # Disable Wi-Fi after using it
        wifi.radio.enabled = False

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
    f_bg = open('imgs/background_zoom.bmp' if plot_zoomed == Zoom.on else 'imgs/background.bmp', 'rb')
    pic = displayio.OnDiskBitmap(f_bg)
    t = displayio.TileGrid(pic, pixel_shader=pic.pixel_shader)
    g.append(t)

    if DEBUG:
        print('Display background drawn.')
        time.sleep(DEBUG_DELAY)

    draw_texts(g, tahoma_font, tahoma_bold_font, ext_temp, ext_humidity, board_temp, board_humidity,
               growth_percentage, peak_percentage, peak_hours)

    if DEBUG:
        print("Labels drawn.")
        time.sleep(DEBUG_DELAY)

    battery_symbol = BatteryWidget(x=257, y=4, width=10, height=19, upper_part_height=2, upper_part_width=4,
                                   background_color=PaletteColor.light_gray, fill_color=PaletteColor.black,
                                   exclamation_mark_threshold=0.038)
    battery_symbol.draw(battery_percentage / 100)
    if battery_symbol.critical_battery and message_lines['am2320'][0] == '':
        message_lines['am2320'] = (' Low battery ', True)
    g.append(battery_symbol)
    g.append(bitmap_label.Label(tahoma_font, color=DARK, text=f'{battery_percentage:.0f}%', x=270, y=13))

    if DEBUG:
        print("Battery symbol drawn.")
        time.sleep(DEBUG_DELAY)

    # Load Wi-Fi bitmap
    if wifi_connectivity is None:
        f_wifi = open('imgs/wifi_none.bmp', 'rb')
    elif telemetry_success:
        f_wifi = open('imgs/wifi_okay.bmp', 'rb')
    else:
        f_wifi = open('imgs/wifi_error.bmp', 'rb')
    wifi_pic = displayio.OnDiskBitmap(f_wifi)
    t = displayio.TileGrid(pic, pixel_shader=pic.wifi_pic, x=232, y=6)
    g.append(t)

    if DEBUG:
        print("Wi-Fi symbol drawn.")
        time.sleep(DEBUG_DELAY)

    # Add the graph plot
    plot = GraphPlot(
        width=296, height=128, origin=(33, 116), top_right=(288, 35), font=tick_font, line_color=PaletteColor.black,
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
    if peak_pos_in_history is not None and plot_type == PlotType.growth:
        plot.plot_peak(value_array, peak_pos_in_history, zoomed=plot_zoomed == Zoom.on)
    g.append(plot)

    # Write message lines
    for key, y_pos in zip(['am2320', 'tmf8821', 'height_calibration'], [50, 70, 90]):
        message, emphasize = message_lines[key]
        if message != '':
            color_fg, color_bg = (WHITE, BLACK) if emphasize else (BLACK, WHITE)
            font = tahoma_bold_font if emphasize else tahoma_font
            g.append(bitmap_label.Label(font, color=color_fg, text=message, x=55, y=y_pos,
                                        background_color=color_bg))

    if DEBUG:
        print("Plot drawing prepared.")
        time.sleep(DEBUG_DELAY)

    # Initialize e-Ink display and immediately write to it, see https://www.good-display.com/news/79.html
    # See --> FAQ #9 "There should be no delay between e-paper initialization and iamge-display.
    # A long delay will put the e-ink in voltage boosting for too long, which is easy to damage the e-ink."
    with busio.SPI(board.SCK, board.MOSI) as spi:
        epd_cs = board.D9
        epd_dc = board.D10
        display_bus = displayio.FourWire(spi, command=epd_dc, chip_select=epd_cs, baudrate=1000000)
        time.sleep(0.1)
        display = adafruit_il0373.IL0373(display_bus, width=296, height=128, rotation=270, black_bits_inverted=INVERTED,
                                         color_bits_inverted=INVERTED, grayscale=True, refresh_time=1, border=None)

        if DEBUG:
            print("display initialized.")
            time.sleep(DEBUG_DELAY)

        display.show(g)
        display.refresh()

        if DEBUG:
            print("Display refreshed.")
            time.sleep(DEBUG_DELAY)

        # Prepare for low power deep sleep
        displayio.release_displays()

    f_wifi.close()
    f_bg.close()

    if DEBUG:
        print("Setting up deep sleep.")
        time.sleep(DEBUG_DELAY)

    sleep_time = INTERVAL_MINUTES * 60
    # If in refrigerator, update everything slower
    if ext_temp is not None and ext_temp < FRIDGE_MAX_TEMP:
        sleep_time *= FRIDGE_SLEEP_TIME_FACTOR
        # To compensate for the x-axis tick distance of 4 min, duplicate the value in the memory
        for _ in range(FRIDGE_SLEEP_TIME_FACTOR - 1):
            if growth_percentage is not None:
                growth_mem.add_value(growth_percentage)
            if ext_temp is not None:
                temp_mem.add_value(ext_temp)

    # If a button was pressed, we assume that the interruption in average occurs after 1/2 of the sleep time
    if wake_reason in ['left', 'middle']:
        # --> wait for 1.5x time to compensate for the early interrupt
        # (we aim at a constant sampling frequency of 4 min)
        sleep_time *= 1.5

    timeout_alarm = alarm.time.TimeAlarm(monotonic_time=t_start - BOOT_TIME + sleep_time)
    left_alarm = alarm.pin.PinAlarm(pin=board.D11, value=False, pull=True)
    middle_alarm = alarm.pin.PinAlarm(pin=board.D12, value=False, pull=True)

    alarm.exit_and_deep_sleep_until_alarms(timeout_alarm, left_alarm, middle_alarm)
    # We will never get *here* -> timeout will force a restart and execute code from the top
except Exception as e:
    exc_string = log_exception_to_sd_card(e)
    if DEBUG:
        print(exc_string)
    raise e
