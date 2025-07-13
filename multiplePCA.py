from adafruit_pca9685 import PCA9685
from adafruit_servokit import ServoKit
import board
import busio

i2c = busio.I2C(board.SCL, board.SDA)

# First board at default address 0x40
pca1 = PCA9685(i2c, address=0x40)
kit1 = ServoKit(channels=16, address=0x40)

# Second board with address 0x41
pca2 = PCA9685(i2c, address=0x41)
kit2 = ServoKit(channels=16, address=0x41)

# Control servos from both boards
kit1.servo[0].angle = 90
kit2.servo[0].angle = 45
