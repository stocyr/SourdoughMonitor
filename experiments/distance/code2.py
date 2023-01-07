import board
from adafruit_ticks import ticks_ms, ticks_diff
from busio import I2C

from lib.tmf8821.adafruit_tmf8821 import TMF8821

i2c = I2C(board.SCL, board.SDA, frequency=125000)

tof = TMF8821(i2c)
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
tof.write_configuration()

oversampling = 1

single = True
print('Starting measurements...')
tof.start_measurements()
while True:
    t_start = ticks_ms()
    if single:
        measurement = tof.wait_for_measurement(timeout_ms=500)
        if tof.config.spad_map == '3x3_normal_mode':
            # print(f'{measurement.distances[4]} \t {measurement.confidences[4]} \t', end='')
            print(f'{measurement.distances[:4] + measurement.distances[:4]} \t', end='')
            print(f'{measurement.confidences[5:] + measurement.confidences[5:]}', end='')
        elif tof.config.spad_map == '3x3_wide_mode':
            print(f'{measurement.distances[4]} \t {measurement.confidences[4]} \t', end='')
        elif tof.config.spad_map == '4x4_normal_mode':
            print(f'{measurement.distances[5:7] + measurement.distances[9:11]} \t', end='')
            print(f'{measurement.confidences[5:7] + measurement.confidences[9:11]}', end='')
        elif tof.config.spad_map == '4x4_narrow_mode':
            print(f'{measurement.distances} \t {measurement.confidences} \t', end='')
    else:
        all_distances = []
        for measurement_repetition in range(oversampling):
            measurement = tof.wait_for_measurement(timeout_ms=500)
            all_distances.extend(measurement.distances[4:5])
        mean_distance = sum(all_distances) / len(all_distances)
        print(f'{mean_distance:.3f}mm', end='')
    t_end = ticks_ms()
    print(f' ({ticks_diff(t_end, t_start)}ms)')
tof.stop_measurements()
