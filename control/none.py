import board, busio
from adafruit_pca9685 import PCA9685

# I2C setup
i2c = busio.I2C(board.SCL, board.SDA)
pca = PCA9685(i2c)
pca.frequency = 50  # 50 Hz for hobby servos

for i in range(16):
        pca.channels[i].duty_cycle = 0