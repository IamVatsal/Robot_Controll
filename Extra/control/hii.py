import json, termios, sys, tty, time
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

# Usage: move channel 1 to 200° out of 270°
# write_angle_270(1, 200)


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


joint_names = list(servo_map.keys())

def hi(): 
    write_angle_270(servo_map["left_chest"], 50)
    time.sleep(1)
    write_angle_270(servo_map["left_shoulder"], 30)
    write_angle_270(servo_map["left_wrist"], 120)
    for i in range(3):
        for j in range(60):
            write_angle_270(servo_map["left_shoulder"], min(30 + j, 65))
            write_angle_270(servo_map["left_wrist"], 120 + j)
            time.sleep(0.05)
        time.sleep(0.5)
        for j in range(60, 0, -1):
            write_angle_270(servo_map["left_shoulder"], max(30, 65 - j))
            write_angle_270(servo_map["left_wrist"], 120 + j)
            time.sleep(0.05)
        time.sleep(0.5)



if __name__ == "__main__":
    hi()
    pca.channels[servo_map["left_chest"]].duty_cycle = 0
    pca.channels[servo_map["left_shoulder"]].duty_cycle = 0
    pca.channels[servo_map["left_wrist"]].duty_cycle = 0
    print("Servo motors set to zero duty cycle.")