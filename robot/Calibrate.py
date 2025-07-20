import json, termios, sys, tty
from robot.util.angle import write_angle_270, release_angle

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
        release_angle(i)
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
        release_angle(i)
    print("All motors released after calibration.")