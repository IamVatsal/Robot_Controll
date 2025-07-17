from adafruit_servokit import ServoKit
import time

# Create servo kit instance for 16 channels
kit = ServoKit(channels=16)

# Move servos 0 through 15 to 90°
for i in range(16):
    kit.servo[i].angle = 90
    time.sleep(0.1)

# Now move each to a different angle to test full range
# for i in range(16):
#     kit.servo[i].angle = 45 + (i * 5) % 90  # just a pattern for demo
#     time.sleep(0.1)
