import board
import adafruit_bitbangio as bitbangio
from adafruit_pca9685 import PCA9685


i2c = bitbangio.I2C(scl=board.D12, sda=board.D16, frequency=100_000)
pca = PCA9685(i2c)
pca.frequency = 50 # 50 Hz for hobby servos

# Helper to compute on/off ticks for a given pulse in microseconds
def set_pulse_us(channel, pulse_us):
    # PCA9685 runs at 50 Hz → 20 ms period → 4096 ticks
    ticks_per_us = 4096 / 20_000
    tick_count = int(pulse_us * ticks_per_us)
    # start at tick 0, end at tick_count
    pca.channels[channel].duty_cycle = int(tick_count * 0xFFFF / 4096)

# Map 0–270° to 500–3000 µs
def write_angle(channel, angle):
    angle = max(0, min(270, angle))
    pulse = 500 + (angle / 270.0) * (3000 - 500)
    set_pulse_us(channel, pulse)

# Usage: move channel 1 to 200° out of 270°
# write_angle_270(1, 200)

# remember to release the servo when done
def release_angle(channel):
    pca.channels[channel].duty_cycle = 0
