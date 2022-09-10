import board
from busio import I2C
from adafruit_tmf8821 import TMF8821
from adafruit_ticks import ticks_ms, ticks_diff

i2c = I2C(board.SCL, board.SDA, frequency=125000)

tof = TMF8821(i2c)
tof.config.iterations = 4E6
tof.config.period_ms = 1000  # as small as possible for repeated measurements
tof.write_configuration()

print('Starting measurements...')
tof.start_measurements()
while True:
    t_start = ticks_ms()
    print(tof.wait_for_measurement(timeout_ms=500))
    t_end = ticks_ms()
    print(f'Took {ticks_diff(t_end, t_start)}ms.')
