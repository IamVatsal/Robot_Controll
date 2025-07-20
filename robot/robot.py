import json
import time
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


servo_map = {
    "left_wrist": 0,
    "left_shoulder": 1,
    "left_chest": 2,
    "left_leg1": 3,
    "left_leg2": 4,
    "left_leg3": 5,
    "left_leg4": 6,
    "left_leg5": 7,
    "right_leg5": 10,
    "right_leg4": 9,
    "right_leg3": 8,
    "right_leg2": 11,
    "right_leg1": 12,
    "right_chest": 13,
    "right_shoulder": 14,
    "right_wrist": 15,
}

class Robot:

    def keyboard_control(self):
        print("Keyboard Servo Control Mode")
        print("Use number keys 1-16 to select joint, ←/→ to move, q to quit.")
        joint_names = list(servo_map.keys())
        selected = 0
        while True:
            current_angle = self.angle_state[joint_names[selected]]
            print(f"\nSelected joint: {joint_names[selected]} (channel {servo_map[joint_names[selected]]}) | Angle: {current_angle}")
            print("Press ←/→ to move, n/p for next/prev joint, q to quit.")
            key = self._getch()
            if key == 'q':
                print("Exiting control mode.")
                break
            elif key == '\x1b':  # arrow keys
                key2 = self._getch(); key3 = self._getch()
                new_angle = current_angle
                if key3 == 'C':  # right arrow
                    new_angle = min(270, current_angle + 5)
                elif key3 == 'D':  # left arrow
                    new_angle = max(0, current_angle - 5)
                if new_angle != current_angle:
                    self._move_joint(joint_names[selected], new_angle - current_angle)
            elif key == 'n':
                selected = (selected + 1) % 16
            elif key == 'p':
                selected = (selected - 1) % 16
            elif key.isdigit() and 1 <= int(key) <= 16:
                selected = int(key) - 1
            time.sleep(0.1)

    def _getch(self):
        import sys, tty, termios
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        tty.setraw(fd)
        ch = sys.stdin.read(1)
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
        return ch
    
    def __init__(self, calibration_path=None):
        self.angle_state = {
            "left_wrist": 155,
            "left_shoulder": 20,
            "left_chest": 262,
            "left_leg1": 135,
            "left_leg2": 157,
            "left_leg3": 257,
            "left_leg4": 149,
            "left_leg5": 190,
            "right_leg5": 20,
            "right_leg4": 134,
            "right_leg3": 30,
            "right_leg2": 80,
            "right_leg1": 145,
            "right_chest": 46,
            "right_shoulder": 51,
            "right_wrist": 117
        }
        if calibration_path:
            self.load_calibration(calibration_path)
        print("Robot initialized with default angles.")

    def load_calibration(self, calibration_path):
        with open(calibration_path, "r") as f:
            calibrated = json.load(f)
        for part, angle in calibrated.items():
            if part in self.angle_state:
                self.angle_state[part] = angle

    def rightWristMove(self, delta):
        self._move_joint('right_wrist', delta)

    def leftWristMove(self, delta):
        self._move_joint('left_wrist', delta)

    def rightShoulderMove(self, delta):
        self._move_joint('right_shoulder', delta)

    def leftShoulderMove(self, delta):
        self._move_joint('left_shoulder', delta)

    def rightChestMove(self, delta):
        self._move_joint('right_chest', delta)

    def leftChestMove(self, delta):
        self._move_joint('left_chest', delta)

    def rightLegMove(self, leg_num, delta):
        key = f"right_leg{leg_num}"
        self._move_joint(key, delta)

    def leftLegMove(self, leg_num, delta):
        key = f"left_leg{leg_num}"
        self._move_joint(key, delta)

    def _move_joint(self, part, delta):
        if part in servo_map:
            new_angle = max(0, min(270, self.angle_state[part] + delta))
            write_angle(servo_map[part], new_angle)
            self.angle_state[part] = new_angle
            print(f"Set {part} to {new_angle}°")
        

    def go_to_standby(self):
        for part, angle in self.angle_state.items():
            write_angle(servo_map[part], angle)
        print("Robot moved to standby/calibrated position.")

    def release_all(self):
        for idx in servo_map.values():
            release_angle(idx)
        print("All servos released.")

if __name__ == "__main__":
    robot = Robot("servo_calibration.json")
    robot.go_to_standby()
    robot.keyboard_control()
    time.sleep(2)
    robot.release_all()
