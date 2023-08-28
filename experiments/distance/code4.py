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

print('Note: 0x31 means that no factory calibration has been loaded, the value of 0x32 means that '
      'the factory calibration does not match to the selected SPAD map.')

tof.single_measurement(500)
calib_state = tof._read_byte(0x07)
print(f'Calib state: {calib_state:0x}')  # 0: success, 31: no factory calibration, 32: factory calib != current setting
# This should return 0x31


# Actually execute factory calibration
# calibration_data = tof._factory_calibration(iterations=4e6)
# Only load existing factory calibration
calibration_data = tof.load_factory_calibration()

# Now print the calibration data as hex on the terminal. During running of this file, the CIRCUITPYTHON drive is in
# read-only mode, so copying from the console print-out and later manually storing to the drive is the solution.
print(f'{" ".join(hex(d) for d in calibration_data)}')
# The following code will convert the hex display print-out to a byte array and store it to a file '3x3_normal_mode_short'
# given the `hex_string` looks like approximately this: hex_string = "0x0 0x1 0x1 0x0 0x1 0xff 0x51 0xf..."
#     byte_array = bytes(int(b, base=16) for b in hex_string.split(' '))
#     with open(Path('3x3_normal_mode_short'), 'wb') as f:
#         f.write(byte_array)

crosstalk_values = [int.from_bytes(calibration_data[0x3C + i * 4: 0x3C + (i + 1) * 4], 'little') for i in range(9)]
print(f'Cross-talk values: {crosstalk_values}')

tof.single_measurement(500)
calib_state = tof._read_byte(0x07)
print(f'Calib state: {calib_state:0x}')  # 0: success, 31: no factory calibration, 32: factory calib != current setting
# This should return 0x00

tof.config.spad_map = '4x4_narrow_mode'
tof.write_configuration()

tof.single_measurement(500)
calib_state = tof._read_byte(0x07)
print(f'Calib state: {calib_state:0x}')  # 0: success, 31: no factory calibration, 32: factory calib != current setting
# This should return 32

tof.config.spad_map = '3x3_normal_mode'
tof.write_configuration()

tof.single_measurement(500)
calib_state = tof._read_byte(0x07)
print(f'Calib state: {calib_state:0x}')  # 0: success, 31: no factory calibration, 32: factory calib != current setting
# This should return 0x00 again


calibration_data = tof.load_factory_calibration()

tof.single_measurement(500)
calib_state = tof._read_byte(0x07)
print(f'Calib state: {calib_state:0x}')  # 0: success, 31: no factory calibration, 32: factory calib != current setting
# This should return 0x00 again
