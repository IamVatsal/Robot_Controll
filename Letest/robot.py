import json
import time
import board
import busio
import threading
import adafruit_bitbangio as bitbangio
from adafruit_pca9685 import PCA9685

#import smbus2

# Directly use I2C bus 3
#i2c_bus = smbus2.SMBus(3) 
#from adafruit_blinka.microcontroller.generic_linux.i2c import I2C as LinuxI2C
#i2c = LinuxI2C(3)

#pca = PCA9685(i2c)
#pca.frequency = 50
#i2c=busio.I2C(board.D12, board.D16)
print("Initializing I2C...")
i2c = bitbangio.I2C(scl=board.D12, sda=board.D16, frequency=100_000)
#i2c = busio.I2C(board.SCL, board.SDA)
print("Trying to lock I2C bus...")
while not i2c.try_lock():
    time.sleep(0.01)

print("Scanning for devices...")
devices = i2c.scan()
print(f"Found devices: {[hex(device) for device in devices]}")

if 0x40 not in devices:
    print("PCA9685 not found at 0x40!")
    i2c.unlock()
    exit()

i2c.unlock()

print("Initializing PCA9685...")
try:
    pca = PCA9685(i2c, address=0x40)
    pca.frequency = 50
    print("PCA9685 initialized successfully!")
except Exception as e:
    print(f"Failed to initialize PCA9685: {e}")
#pca = PCA9685(i2c)
#pca.frequency = 50 # 50 Hz for hobby servos
# Use default SCL/SDA, but now routed to GPIO12/16 via i2c-3
#i2c = busio.I2C(board.SCL, board.SDA)

# Wait until I2C bus is ready
#while not i2c.try_lock():
#    pass
#i2c.unlock()

# Initialize PCA9685
#pca = PCA9685(i2c)
#pca.frequency = 50
#from adafruit_blinka.microcontroller.generic_linux.i2c import I2C as HardwareI2C
#from smbus2 import SMBus
#i2c = SMBus(3)  # because /dev/i2c-3
#pca = PCA9685(i2c)
#pca.frequency = 50

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
    "right_wrist": 13,#damage
    "right_shoulder": 9,
    "right_chest": 10,
    "right_leg1": 11,
    "right_leg2": 12,
    "right_leg3": 8,
    "right_leg4": 14,
    "right_leg5": 15,
}

class Robot:

    def __init__(self, calibration_path=None):
        self.angle_state = {
            "left_wrist": 155,
            "left_shoulder": 180,
            "left_chest": 65,
            "left_leg1": 15,
            "left_leg2": 122,
            "left_leg3": 202,
            "left_leg4": 149,
            "left_leg5": 140,
            "right_leg5": 0,
            "right_leg4": 149,
            "right_leg3": 25,
            "right_leg2": 85,
            "right_leg1": 205,
            "right_chest": 46,
            "right_shoulder": 116,
            "right_wrist": 117
        }
        if calibration_path:
            self.load_calibration(calibration_path)
        print("Robot initialized with default angles.")

    def keyboard_control(self):
        print("🎮 Keyboard Servo Control Mode")
        print("Use number keys 1-16 to select joint, ←/→ to move, special commands:")
        print("  w = walk forward (3 steps)")
        print("  s = single step forward") 
        print("  h = say hi gesture")
        print("  r = return to standby")
        print("  q = quit")
        
        joint_names = list(servo_map.keys())
        selected = 0
        
        while True:
            current_angle = self.angle_state[joint_names[selected]]
            print(f"\nSelected: {joint_names[selected]} (Ch{servo_map[joint_names[selected]]}) | Angle: {current_angle}°")
            print("Controls: ←/→ = ±5°, n/p = next/prev joint, w/s/h/r/q = special commands")
            
            key = self._getch()
            
            if key == 'q':
                print("👋 Exiting control mode.")
                break
            elif key == 'w':
                print("🚶‍♂️ Walking forward...")
                self.walk_forward(3)
            elif key == 's':
                print("👣 Single step...")
                self.step_forward()
            elif key == 'h':
                print("👋 Hi gesture...")
                self.say_hi()
            elif key == 'r':
                print("🏠 Returning to standby...")
                self.go_to_standby()
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

    def say_hi_left(self):
        print("👋 Starting hi gesture...")
        
        # Store original positions to restore later
        original_chest = self.angle_state["left_chest"]
        original_shoulder = self.angle_state["left_shoulder"] 
        original_wrist = self.angle_state["left_wrist"]
        
        try:
            # Initial positioning
            write_angle(servo_map["left_chest"], 50)
            self.angle_state["left_chest"] = 50
            time.sleep(1)
            
            write_angle(servo_map["left_shoulder"], 30)
            self.angle_state["left_shoulder"] = 30
            
            write_angle(servo_map["left_wrist"], 120)
            self.angle_state["left_wrist"] = 120
            
            # Waving motion - 3 cycles
            for i in range(3):
                print(f"  Wave cycle {i+1}/3")
                
                # Wave up
                for j in range(60):
                    shoulder_angle = min(30 + j, 65)
                    wrist_angle = 120 + j
                    
                    write_angle(servo_map["left_shoulder"], shoulder_angle)
                    write_angle(servo_map["left_wrist"], wrist_angle)
                    
                    self.angle_state["left_shoulder"] = shoulder_angle
                    self.angle_state["left_wrist"] = wrist_angle
                    
                    time.sleep(0.01)
                
                time.sleep(0.1)
                
                # Wave down
                for j in range(60, 0, -1):
                    shoulder_angle = max(30, 65 - (60 - j))
                    wrist_angle = 120 + j
                    
                    write_angle(servo_map["left_shoulder"], shoulder_angle)
                    write_angle(servo_map["left_wrist"], wrist_angle)
                    
                    self.angle_state["left_shoulder"] = shoulder_angle
                    self.angle_state["left_wrist"] = wrist_angle
                    
                    time.sleep(0.01)
                
                time.sleep(0.1)
            
            print("✅ Hi gesture completed!")
        
        except Exception as e:
            print(f"❌ Error during hi gesture: {e}")
        
        finally:
            # Return to original positions
            print("🔄 Returning to original positions...")
            write_angle(servo_map["left_chest"], original_chest)
            write_angle(servo_map["left_shoulder"], original_shoulder)
            write_angle(servo_map["left_wrist"], original_wrist)

            self.angle_state["left_chest"] = original_chest
            self.angle_state["left_shoulder"] = original_shoulder
            self.angle_state["left_wrist"] = original_wrist
            
            time.sleep(1)

    def say_hi_right(self):
        print("👋 Starting hi gesture...")
        
        # Store original positions to restore later
        original_chest = self.angle_state["right_chest"]
        original_shoulder = self.angle_state["right_shoulder"] 
        original_wrist = self.angle_state["right_wrist"]
        
        try:
            # Initial positioning
            write_angle(servo_map["right_chest"], 46)
            self.angle_state["right_chest"] = 46
            time.sleep(1)

            write_angle(servo_map["right_shoulder"], 116)
            self.angle_state["right_shoulder"] = 116

            write_angle(servo_map["right_wrist"], 120)
            self.angle_state["right_wrist"] = 120

            # Waving motion - 3 cycles
            for i in range(3):
                print(f"  Wave cycle {i+1}/3")
                
                # Wave up
                for j in range(140):
                    shoulder_angle = min(116 + j, 250)
                    wrist_angle = 120 + j
                    
                    write_angle(servo_map["right_shoulder"], shoulder_angle)
                    write_angle(servo_map["right_wrist"], wrist_angle)
                    
                    self.angle_state["right_shoulder"] = shoulder_angle
                    self.angle_state["right_wrist"] = wrist_angle
                    
                    time.sleep(0.01)
                
                time.sleep(0.1)
                
                # Wave down
                for j in range(140, 0, -1):
                    shoulder_angle = max(116, 250 - (140 - j))
                    wrist_angle = 120 + j

                    write_angle(servo_map["right_shoulder"], shoulder_angle)
                    write_angle(servo_map["right_wrist"], wrist_angle)

                    self.angle_state["right_shoulder"] = shoulder_angle
                    self.angle_state["right_wrist"] = wrist_angle
                    
                    time.sleep(0.01)
                
                time.sleep(0.1)
            
            print("✅ Hi gesture completed!")
        
        except Exception as e:
            print(f"❌ Error during hi gesture: {e}")
        
        finally:
            # Return to original positions
            print("🔄 Returning to original positions...")
            write_angle(servo_map["right_chest"], original_chest)
            write_angle(servo_map["right_shoulder"], original_shoulder)
            write_angle(servo_map["right_wrist"], original_wrist)

            self.angle_state["right_chest"] = original_chest
            self.angle_state["right_shoulder"] = original_shoulder
            self.angle_state["right_wrist"] = original_wrist

            time.sleep(1)

    def say_hi_both(self):
        print("👋 Starting both hands hi gesture...")
    
        # Create threads for each hand
        left_thread = threading.Thread(target=self.say_hi_left)
        right_thread = threading.Thread(target=self.say_hi_right)

        # Start both threads simultaneously
        left_thread.start()
        right_thread.start()

        # Wait for both to complete
        left_thread.join()
        right_thread.join()

        print("✅ Both hands hi gesture completed!")

    def release_all(self):
        for idx in servo_map.values():
            release_angle(idx)
        print("All servos released.")

    # ============== WALKING SYSTEM ==============

    def set_servo_angle(self, servo_id, angle):
        """Set a servo angle directly using the existing write_angle function"""
        angle = max(0, min(270, angle))  # Clamp to valid range
        write_angle(servo_id, angle)
        
        # Update internal state if this servo is in our map
        for part_name, channel in servo_map.items():
            if channel == servo_id:
                self.angle_state[part_name] = angle
                break

    def move_servo_smooth(self, servo_id, start_angle, end_angle, step=1, delay=0.01):
        """Move servo smoothly from start_angle to end_angle"""
        start_angle = max(0, min(270, start_angle))
        end_angle = max(0, min(270, end_angle))
        
        if start_angle == end_angle:
            return
            
        # Determine direction
        if start_angle < end_angle:
            angles = range(int(start_angle), int(end_angle) + 1, abs(step))
        else:
            angles = range(int(start_angle), int(end_angle) - 1, -abs(step))
        
        # Move through each angle
        for angle in angles:
            self.set_servo_angle(servo_id, angle)
            time.sleep(delay)
        
        # Ensure we end at the exact target angle
        self.set_servo_angle(servo_id, end_angle)

    def get_current_servo_angle(self, part_name):
        """Get current angle for a servo part"""
        return self.angle_state.get(part_name, 90)  # Default to 90 if not found

    # Walking stance and weight shifting functions
    def shift_weight_to_left(self):
        """Shift robot's weight to the left leg for right leg movement"""
        print("🔄 Shifting weight to left leg...")
        
        # Tilt body slightly left by adjusting chest servos
        current_left_chest = self.get_current_servo_angle("left_chest")
        current_right_chest = self.get_current_servo_angle("right_chest")
        
        # Shift weight by tilting chest
        target_left_chest = min(270, current_left_chest + 15)  # Lean left
        target_right_chest = max(0, current_right_chest - 10)   # Counterbalance
        
        self.move_servo_smooth(servo_map["left_chest"], current_left_chest, target_left_chest, 2, 0.02)
        self.move_servo_smooth(servo_map["right_chest"], current_right_chest, target_right_chest, 2, 0.02)
        
        # Adjust leg stance for stability
        self.move_servo_smooth(servo_map["left_leg2"], self.get_current_servo_angle("left_leg2"), 
                              max(0, self.get_current_servo_angle("left_leg2") - 10), 2, 0.02)
        
        time.sleep(0.3)  # Allow weight to settle

    def shift_weight_to_right(self):
        """Shift robot's weight to the right leg for left leg movement"""
        print("🔄 Shifting weight to right leg...")
        
        # Tilt body slightly right by adjusting chest servos
        current_left_chest = self.get_current_servo_angle("left_chest")
        current_right_chest = self.get_current_servo_angle("right_chest")
        
        # Shift weight by tilting chest
        target_left_chest = max(0, current_left_chest - 10)    # Counterbalance
        target_right_chest = min(270, current_right_chest + 15) # Lean right
        
        self.move_servo_smooth(servo_map["left_chest"], current_left_chest, target_left_chest, 2, 0.02)
        self.move_servo_smooth(servo_map["right_chest"], current_right_chest, target_right_chest, 2, 0.02)
        
        # Adjust leg stance for stability
        self.move_servo_smooth(servo_map["right_leg2"], self.get_current_servo_angle("right_leg2"), 
                              max(0, self.get_current_servo_angle("right_leg2") - 10), 2, 0.02)
        
        time.sleep(0.3)  # Allow weight to settle

    def lift_right_leg(self):
        """Lift the right leg for forward movement"""
        print("🦵 Lifting right leg...")
        
        # Lift the leg by bending knee (leg3) and hip (leg2)
        current_leg2 = self.get_current_servo_angle("right_leg2")
        current_leg3 = self.get_current_servo_angle("right_leg3")
        
        # Bend knee to lift foot
        target_leg3 = min(270, current_leg3 + 30)  # Bend knee more
        target_leg2 = min(270, current_leg2 + 20)  # Lift thigh
        
        self.move_servo_smooth(servo_map["right_leg3"], current_leg3, target_leg3, 2, 0.03)
        self.move_servo_smooth(servo_map["right_leg2"], current_leg2, target_leg2, 2, 0.03)
        
        time.sleep(0.2)

    def move_right_leg_forward(self):
        """Move the right leg forward while lifted"""
        print("➡️ Moving right leg forward...")
        
        # Move hip forward (leg1) to swing leg forward
        current_leg1 = self.get_current_servo_angle("right_leg1")
        target_leg1 = min(270, current_leg1 + 25)  # Swing forward
        
        self.move_servo_smooth(servo_map["right_leg1"], current_leg1, target_leg1, 2, 0.03)
        
        time.sleep(0.2)

    def place_right_leg_down(self):
        """Place the right leg down after forward movement"""
        print("⬇️ Placing right leg down...")
        
        # Lower the leg by straightening knee and hip
        current_leg2 = self.get_current_servo_angle("right_leg2")
        current_leg3 = self.get_current_servo_angle("right_leg3")
        
        # Straighten leg to place foot down
        target_leg3 = max(0, current_leg3 - 30)  # Straighten knee
        target_leg2 = max(0, current_leg2 - 20)  # Lower thigh
        
        self.move_servo_smooth(servo_map["right_leg3"], current_leg3, target_leg3, 2, 0.03)
        self.move_servo_smooth(servo_map["right_leg2"], current_leg2, target_leg2, 2, 0.03)
        
        time.sleep(0.3)

    def lift_left_leg(self):
        """Lift the left leg for forward movement"""
        print("🦵 Lifting left leg...")
        
        # Lift the leg by bending knee (leg3) and hip (leg2)
        current_leg2 = self.get_current_servo_angle("left_leg2")
        current_leg3 = self.get_current_servo_angle("left_leg3")
        
        # Bend knee to lift foot
        target_leg3 = max(0, current_leg3 - 30)   # Bend knee more (opposite direction from right)
        target_leg2 = max(0, current_leg2 - 20)   # Lift thigh
        
        self.move_servo_smooth(servo_map["left_leg3"], current_leg3, target_leg3, 2, 0.03)
        self.move_servo_smooth(servo_map["left_leg2"], current_leg2, target_leg2, 2, 0.03)
        
        time.sleep(0.2)

    def move_left_leg_forward(self):
        """Move the left leg forward while lifted"""
        print("➡️ Moving left leg forward...")
        
        # Move hip forward (leg1) to swing leg forward
        current_leg1 = self.get_current_servo_angle("left_leg1")
        target_leg1 = max(0, current_leg1 - 25)  # Swing forward (opposite direction from right)
        
        self.move_servo_smooth(servo_map["left_leg1"], current_leg1, target_leg1, 2, 0.03)
        
        time.sleep(0.2)

    def place_left_leg_down(self):
        """Place the left leg down after forward movement"""
        print("⬇️ Placing left leg down...")
        
        # Lower the leg by straightening knee and hip
        current_leg2 = self.get_current_servo_angle("left_leg2")
        current_leg3 = self.get_current_servo_angle("left_leg3")
        
        # Straighten leg to place foot down
        target_leg3 = min(270, current_leg3 + 30)  # Straighten knee
        target_leg2 = min(270, current_leg2 + 20)  # Lower thigh
        
        self.move_servo_smooth(servo_map["left_leg3"], current_leg3, target_leg3, 2, 0.03)
        self.move_servo_smooth(servo_map["left_leg2"], current_leg2, target_leg2, 2, 0.03)
        
        time.sleep(0.3)

    def return_to_center_stance(self):
        """Return body to center stance after walking"""
        print("🏠 Returning to center stance...")
        
        # Return chest to neutral position
        self.move_servo_smooth(servo_map["left_chest"], 
                              self.get_current_servo_angle("left_chest"), 
                              self.angle_state["left_chest"], 2, 0.02)
        self.move_servo_smooth(servo_map["right_chest"], 
                              self.get_current_servo_angle("right_chest"), 
                              self.angle_state["right_chest"], 2, 0.02)
        
        time.sleep(0.5)

    def step_forward(self):
        """Execute one full walking step (right leg forward, then left leg forward)"""
        print("\n🚶 Executing one forward step...")
        
        try:
            # Right leg step
            self.shift_weight_to_left()
            self.lift_right_leg()
            self.move_right_leg_forward()
            self.place_right_leg_down()
            
            # Left leg step
            self.shift_weight_to_right()
            self.lift_left_leg()
            self.move_left_leg_forward()
            self.place_left_leg_down()
            
            # Return to center
            self.return_to_center_stance()
            
            print("✅ Step completed successfully!")
            
        except Exception as e:
            print(f"❌ Error during step: {e}")
            # Emergency return to standby
            self.go_to_standby()

    def walk_forward(self, steps=3):
        """Repeat the step_forward() function for the given number of steps"""
        print(f"\n🚶‍♂️ Starting forward walk - {steps} steps")
        
        try:
            for i in range(steps):
                print(f"\n--- Step {i+1}/{steps} ---")
                self.step_forward()
                
                # Brief pause between steps
                if i < steps - 1:  # Don't pause after the last step
                    print("⏸️ Brief pause...")
                    time.sleep(0.5)
            
            print(f"\n🎉 Walk completed! {steps} steps taken.")
            
        except Exception as e:
            print(f"❌ Error during walk: {e}")
            # Emergency return to standby
            self.go_to_standby()

    def walk_demo(self):
        """Demonstration of walking capabilities"""
        print("\n🤖 WALKING DEMONSTRATION")
        print("=" * 40)
        
        try:
            print("1. Moving to standby position...")
            self.go_to_standby()
            time.sleep(2)
            
            print("2. Starting 3-step forward walk...")
            self.walk_forward(3)
            
            print("3. Walk demonstration complete!")
            
        except Exception as e:
            print(f"❌ Demo error: {e}")
        finally:
            print("4. Returning to safe standby position...")
            self.go_to_standby()

def init_robot(input,logger, calibration_path=None):
    """Initialize the robot with optional calibration file"""
    robot = Robot(calibration_path)
    robot.go_to_standby()
    handle_input(robot,logger, input)

    return robot

def handle_input(robot,logger,input):

    if(input == "no_movement"):
        logger.warning("No movement command received.")
    elif(input == "stand_by"):
        logger.warning(f"stand_by: {input}")
        #robot = Robot()
        robot.go_to_standby()
    # elif (input == "right_leg_forward"):
    #     print("Moving right leg forward...")
    #     robot.rightLegMove(1, 10)
    # elif(input == "left_leg_forward"):
    #     print("Moving left leg forward...")
    #     robot.leftLegMove(1, 10)
    elif(input == "right_hand_wave"):
        logger.warning("Waving right hand...")
        robot.say_hi_right()
    elif(input == "left_hand_wave"):
        logger.warning("Waving left hand...")
        robot.say_hi_left()
        # robot.leftHandWave()
    elif(input == "right_hand_raise"):
        logger.warning("Raising right hand...")
        robot.say_hi_left()
        # robot.rightHandRaise()
    elif(input == "left_hand_raise"):
        logger.warning("Raising left hand...")
        robot.say_hi_left()
        # robot.leftHandRaise()
    elif(input == "both_hands_raise"):
        logger.warning("Raising both hands...")
        robot.say_hi_both()
    elif(input == "walk_forward"):
        logger.warning("Walking forward...")
        robot.walk_demo()


if __name__ == "__main__":
    robot = Robot()
    robot.go_to_standby()
    
    print("\n🤖 Robot Control Options:")
    print("1. Press 'k' for keyboard control")
    print("2. Press 'w' for walking demo")
    print("3. Press 'h' for hi gesture")
    print("4. Press 'b' for both hands raise")
    print("5. Press 'q' to quit")
    
    while True:
         print("\nEnter command: ", end="", flush=True)
         try:
             key = robot._getch()
             if key == 'k':
                 robot.keyboard_control()
             elif key == 'w':
                 robot.walk_demo()
             elif key == 'b':
                 robot.say_hi_left()
                 robot.say_hi_right()
             elif key == 'h':
                 robot.say_hi_right()
             elif key == 'q':
                 break
             else:
                 print(f"Unknown command: {key}")
         except KeyboardInterrupt:
             break
    
    print("\n🔄 Releasing all servos...")
    time.sleep(2)
    robot.release_all()