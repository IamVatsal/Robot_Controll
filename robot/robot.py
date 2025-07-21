import json
import time
from robot.util.angle import write_angle, release_angle


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

    def say_hi(self):
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
                    
                    time.sleep(0.05)
                
                time.sleep(0.5)
                
                # Wave down
                for j in range(60, 0, -1):
                    shoulder_angle = max(30, 65 - (60 - j))
                    wrist_angle = 120 + j
                    
                    write_angle(servo_map["left_shoulder"], shoulder_angle)
                    write_angle(servo_map["left_wrist"], wrist_angle)
                    
                    self.angle_state["left_shoulder"] = shoulder_angle
                    self.angle_state["left_wrist"] = wrist_angle
                    
                    time.sleep(0.05)
                
                time.sleep(0.5)
            
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
