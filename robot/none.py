import board
import adafruit_bitbangio as bitbangio
from adafruit_pca9685 import PCA9685


i2c = bitbangio.I2C(scl=board.D12, sda=board.D16, frequency=100_000)
pca = PCA9685(i2c)
pca.frequency = 50 # 50 Hz for hobby servos

def release_angle(channel):
    pca.channels[channel].duty_cycle = 0


for i in range(16):
        release_angle(i)

print("All servos released.")