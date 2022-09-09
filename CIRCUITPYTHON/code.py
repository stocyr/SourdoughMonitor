import board
from busio import I2C
from adafruit_tmf8821 import TMF8821

i2c = I2C(board.SCL, board.SDA, frequency=125000)

tof = TMF8821(i2c)
