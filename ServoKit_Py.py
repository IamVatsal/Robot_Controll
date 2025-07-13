from adafruit_servokit import ServoKit
import time

# Use 16-channel PCA9685
kit = ServoKit(channels=16)

# Example: assuming 6 servos (legs, arms, head etc.)
# Set all servos to 90° (neutral position)
def go_to_default_pose():
    default_angles = [90, 90, 90, 90, 90, 90]  # Change as needed
    for i, angle in enumerate(default_angles):
        kit.servo[i].angle = angle
        time.sleep(0.2)

print("Moving to default pose...")
go_to_default_pose()
print("Done.")
