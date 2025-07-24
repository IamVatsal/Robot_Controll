from adafruit_servokit import ServoKit
import time

kit = ServoKit(channels=16)

# Servo ID map
servo_map = {
    "left_wrist": 0,
    "left_shoulder": 1,
    "left_chest": 2,
    "left_leg1": 3,
    "left_leg2": 4,
    "left_leg3": 5,
    "left_leg4": 6,
    "left_leg5": 7,
    "right_wrist": 15,
    "right_shoulder": 14,
    "right_chest": 13,
    "right_leg1": 12,
    "right_leg2": 11,
    "right_leg3": 10,
    "right_leg4": 9,
    "right_leg5": 8
}



def move_servo(name, angle):
    servo_id = servo_map[name]
    kit.servo[servo_id].angle = angle
    time.sleep(0.5)

def right_hand_up():
    print("Right hand up")
    move_servo("right_shoulder", 30)  # adjust angle as per your robot
    move_servo("right_wrist", 90)

def right_hand_down():
    print("Right hand down")
    move_servo("right_shoulder", 90)
    move_servo("right_wrist", 90)

def left_hand_up():
    print("Left hand up")
    move_servo("left_shoulder", 150)  # adjust as needed
    move_servo("left_wrist", 90)

def left_hand_down():
    print("Left hand down")
    move_servo("left_shoulder", 90)
    move_servo("left_wrist", 90)

def right_leg_up():
    print("Right leg up")
    move_servo("right_leg1", 60)
    move_servo("right_leg2", 60)

def right_leg_down():
    print("Right leg down")
    move_servo("right_leg1", 90)
    move_servo("right_leg2", 90)

def left_leg_up():
    print("Left leg up")
    move_servo("left_leg1", 120)
    move_servo("left_leg2", 120)

def left_leg_down():
    print("Left leg down")
    move_servo("left_leg1", 90)
    move_servo("left_leg2", 90)

def standby_pose():
    print("Entering standby pose...")
    for part in servo_map:
        move_servo(part, 90)

def say_hi():
    print("Waving hello!")
    move_servo("right_shoulder", 30)  # hand up
    for _ in range(2):
        move_servo("right_wrist", 60)
        time.sleep(0.5)
        move_servo("right_wrist", 120)
        time.sleep(0.5)
    right_hand_down()


import time

last_action = time.time()


if __name__ == "__main__":
        
    # Main loop
    while True:
        # Simulate input (replace with real event logic)
        say_hi()
        last_action = time.time()
    
        # Wait for 10 sec of inactivity
        while time.time() - last_action < 10:
            time.sleep(1)
    
        standby_pose()
    