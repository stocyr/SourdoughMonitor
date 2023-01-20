# Factory calibration

import board
from adafruit_ticks import ticks_ms, ticks_diff
from busio import I2C

from lib.tmf8821 import TMF8821

i2c = I2C(board.SCL, board.SDA, frequency=125000)

tof = TMF8821(i2c, verbose=True)

tof.config.iterations = 4e6
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
tof.config.spread_spectrum_factor = 3
tof.write_configuration()
tof.active_range = 'short'

print('Note: 0x31 means that no factory calibration has been loaded, the value of 0x32 means that
      'the factory calibration does not match to the selected SPAD map.')

tof.single_measurement()
calib_state = tof._read_byte(0x07)
print(f'Calib state: {calib_state:0x}')  # 0: success, 31: no factory calibration, 32: factory calib != current setting
# This should return 0x31


# Actually execute factory calibration
calibration_data = tof.store_factory_calibration(iterations=4e6)
# Only load existing factory calibration
# calibration_data = tof.load_factory_calibration()

print(f'{" ".join(hex(d) for d in calibration_data)}')

crosstalk_values = [int.from_bytes(calibration_data[0x3C + i * 4: 0x3C + (i + 1) * 4], 'little') for i in range(9)]
print(f'Cross-talk values: {crosstalk_values}')

tof.single_measurement()
calib_state = tof._read_byte(0x07)
print(f'Calib state: {calib_state:0x}')  # 0: success, 31: no factory calibration, 32: factory calib != current setting
# This should return 0x00

tof.config.spad_map = '4x4_narrow_mode'
tof.write_configuration()

tof.single_measurement()
calib_state = tof._read_byte(0x07)
print(f'Calib state: {calib_state:0x}')  # 0: success, 31: no factory calibration, 32: factory calib != current setting
# This should return 32

tof.config.spad_map = '3x3_normal_mode'

tof.single_measurement()
calib_state = tof._read_byte(0x07)
print(f'Calib state: {calib_state:0x}')  # 0: success, 31: no factory calibration, 32: factory calib != current setting
# This should return 0x00 again
