import json, termios, sys, tty
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


## ServoKit code removed; only PCA9685 is used
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

calibrated = {}  # will hold your saved angles

def getch():
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    tty.setraw(fd)
    ch = sys.stdin.read(1)
    termios.tcsetattr(fd, termios.TCSADRAIN, old)
    return ch

def calibrate(part):
    chan = servo_map[part]
    angle = 135
    print(f"\nCalibrating {part}. ←/→ to adjust (0-270), s to save, q to quit")
    while True:
        try:
            write_angle_270(chan, angle)
            print(f"\r  {part}: {angle:3d}°  ", end="", flush=True)
        except Exception as e:
            print(f"\r  {part}: {angle:3d}° (ERROR)  ", end="", flush=True)

        key = getch()
        if key == '\x1b':  # arrow      (some terminals send escape codes)
            key2 = getch(); key3 = getch()
            if key3 == 'C':   angle = min(270, angle + 1)  # right
            elif key3 == 'D': angle = max(0, angle - 1)    # left

        elif key.lower() == 's':
            calibrated[part] = angle
            print(f"\n Saved {part} = {angle}°")
            break
        elif key.lower() == 'q':
            print("\nExiting calibration.")
            sys.exit(0)

if __name__ == "__main__":
    # Release all motors before calibration
    for i in range(16):
        pca.channels[i].duty_cycle = 0
    print("All motors released before calibration.")

    for part in servo_map:
        print(f"\nStarting calibration for {part}...")
        calibrate(part)

    # write out a JSON file you can import in your main code
    with open("servo_calibration.json", "w") as f:
        json.dump(calibrated, f, indent=2)
    print("Calibration complete!  Values saved to servo_calibration.json")

    # Release all motors after calibration
    for i in range(16):
        pca.channels[i].duty_cycle = 0
    print("All motors released after calibration.")