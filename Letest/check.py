#!/usr/bin/env python3
import os

# Must come before any Blinka imports!
os.environ["BLINKA_I2C_BUS"] = "3"

import board
import busio
from adafruit_pca9685 import PCA9685

# Open the I²C bus 3 (GPIO 16=SDA, 12=SCL overlay)
i2c = busio.I2C(board.SCL, board.SDA)

# Wait until the bus is ready
while not i2c.try_lock():
    pass

devices = i2c.scan()
i2c.unlock()

print("I2C devices on bus 3:", [hex(addr) for addr in devices])

if 0x40 in devices:
    pca = PCA9685(i2c)
    pca.frequency = 50
    for ch in range(16):
        pca.channels[ch].duty_cycle = 0
    print("✅ PCA9685 on bus 3 initialized and all servos released.")
else:
    print("⚠️ PCA9685 not found at 0x40 on bus 3. Check overlay and wiring.")
