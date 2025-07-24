import json, termios, sys, tty, time
import board
import adafruit_bitbangio as bitbangio
from adafruit_pca9685 import PCA9685


i2c = bitbangio.I2C(scl=board.D12, sda=board.D16)
pca = PCA9685(i2c)
pca.frequency = 50 # 50 Hz for hobby servos



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

# Helper to get a single keypress

def getch():
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    tty.setraw(fd)
    ch = sys.stdin.read(1)
    termios.tcsetattr(fd, termios.TCSADRAIN, old)
    return ch

def keyboard_control():
    print("Keyboard Servo Control Mode")
    print("Use number keys 1-16 to select joint, ←/→ to move, q to quit.")
    selected = 0
    angles = [90] * 16
    while True:
        print(f"\nSelected joint: {joint_names[selected]} (channel {servo_map[joint_names[selected]]}) | Angle: {angles[selected]}")
        print("Press ←/→ to move, n/p for next/prev joint, q to quit.")
        key = getch()
        if key == 'q':
            print("Exiting control mode.")
            break
        elif key == '\x1b':  # arrow keys
            key2 = getch(); key3 = getch()
            if key3 == 'C':  # right arrow
                angles[selected] = min(270, angles[selected] + 5)
            elif key3 == 'D':  # left arrow
                angles[selected] = max(0, angles[selected] - 5)
            write_angle_270(selected, angles[selected])
            print(f"Moved {joint_names[selected]} to {angles[selected]}°")
        elif key == 'n':
            selected = (selected + 1) % 16
        elif key == 'p':
            selected = (selected - 1) % 16
        elif key.isdigit() and 1 <= int(key) <= 16:
            selected = int(key) - 1
        time.sleep(0.1)

if __name__ == "__main__":
    keyboard_control()
