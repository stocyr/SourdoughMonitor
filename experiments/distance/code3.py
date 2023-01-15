# Tries out the new short range optimization and spread_spectrum factor > 0

import board
from adafruit_ticks import ticks_ms, ticks_diff
from busio import I2C

from lib.tmf8821 import TMF8821

i2c = I2C(board.SCL, board.SDA, frequency=125000)

tof = TMF8821(i2c, verbose=True)

tof.config.iterations = 3.5e6
tof.config.period_ms = 1  # as small as possible for repeated measurements

'''
'3x3_normal_mode': 1,
'3x3_macro_mode_upper': 2,
'3x3_macro_mode_lower': 3,
'3x3_wide_mode': 6,
'3x3_checkerboard_mode': 11,
'3x3_inverted_checkerboard_mode': 12,
'4x4_normal_mode': 7,
'4x4_macro_mode_upper': 4,
'4x4_macro_mode_lower': 5,
'4x4_narrow_mode': 13,
'3x6_mode': 10,
'''
tof.config.spad_map = '3x3_normal_mode'
tof.config.spread_spectrum_factor = 5

tof.write_configuration()

tof.active_range = 'short'

if True:
    print('Starting measurements...')
    tof.start_measurements()
    while True:
        t_start = ticks_ms()
        measurement = tof.wait_for_measurement(timeout_ms=500)
        # Calibration
        distances = [m for m in measurement.distances]
        print(' '.join(map(str, distances)), ' '.join(map(str, measurement.confidences)), end='')
        t_end = ticks_ms()
        print(f' (in {ticks_diff(t_end, t_start)}ms)')
