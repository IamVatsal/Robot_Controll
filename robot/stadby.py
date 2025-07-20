import json, termios, sys, tty, time
import adafruit_blinka.microcontroller.bcm283x.pin as pin
import adafruit_bitbangio as bitbangio
from adafruit_pca9685 import PCA9685

sda = pin.D12
scl = pin.D16
# I2C setup
i2c = bitbangio.I2C(sda, scl, frequency=100_000)  # 100 kHz I2C
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

servo_map = {
    "left_wrist": 0,
    "left_shoulder": 1,
    "left_chest": 2,
    "left_leg1": 3,
    "left_leg2": 4,
    "left_leg3": 5,
    "left_leg4": 6,
    "left_leg5": 7,
    "right_leg5": 8,
    "right_leg4": 9,
    "right_leg3": 10,
    "right_leg2": 11,
    "right_leg1": 12,
    "right_chest": 13,
    "right_shoulder": 14,
    "right_wrist": 15,
}

# Standby function to set all servos to their calibrated angles
def standby(calibration_path):
    with open(calibration_path, "r") as f:
        calibrated = json.load(f)
    for part, angle in calibrated.items():
        channel = servo_map.get(part)
        if channel is not None:
            write_angle_270(channel, angle)
    print("All servos set to standby/calibrated positions.")

if __name__ == "__main__":
    calibration_file = "servo_calibration.json"
    try:
        standby(calibration_file)
    except FileNotFoundError:
        print(f"Calibration file '{calibration_file}' not found. Please calibrate first.")
    except Exception as e:
        print(f"An error occurred: {e}")