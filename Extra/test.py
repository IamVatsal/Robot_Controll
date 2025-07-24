import board, busio
from adafruit_pca9685 import PCA9685

# I2C setup
i2c = busio.I2C(board.SCL, board.SDA)
pca = PCA9685(i2c)
pca.frequency = 50  # 50 Hz for hobby servos

# Helper to compute on/off ticks for a given pulse in microseconds
def set_pulse_us(channel, pulse_us):
    # PCA9685 runs at 50 Hz → 20 ms period → 4096 ticks
    ticks_per_us = 4096 / 20_000
    tick_count = int(pulse_us * ticks_per_us)
    # start at tick 0, end at tick_count
    pca.channels[channel].duty_cycle = int(tick_count * 0xFFFF / 4096)

# Map 0–270° to 500–2700 µs
def write_angle_270(channel, angle):
    pulse = 300 + (angle / 270.0) * (2900 - 300)
    set_pulse_us(channel, pulse)


write_angle_270(0, 90)  # Example usage: move channel 1 to 200° out of 270°
