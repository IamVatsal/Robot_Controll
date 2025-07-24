import json
import sys
import time
import os

# Cross-platform hardware setup
try:
    import board
    import adafruit_bitbangio as bitbangio
    from adafruit_pca9685 import PCA9685
    
    # Initialize I2C and PCA9685 (matching your robot.py setup)
    i2c = bitbangio.I2C(scl=board.D12, sda=board.D16, frequency=100_000)
    pca = PCA9685(i2c)
    pca.frequency = 50  # 50 Hz for hobby servos
    
    HARDWARE_AVAILABLE = True
    print("✅ Hardware initialized successfully")
    
except ImportError as e:
    print(f"⚠️  Hardware modules not available: {e}")
    print("Running in simulation mode...")
    HARDWARE_AVAILABLE = False
    
    # Mock PCA class for testing
    class MockPCA:
        def __init__(self):
            self.frequency = 50
            self.channels = [type('Channel', (), {'duty_cycle': 0})() for _ in range(16)]
    
    pca = MockPCA()

# Cross-platform getch function
def getch():
    """Get single character from keyboard - cross-platform"""
    try:
        # Windows
        import msvcrt
        key = msvcrt.getch()
        if key == b'\xe0':  # Arrow key prefix
            key2 = msvcrt.getch()
            if key2 == b'M': return 'RIGHT'
            elif key2 == b'K': return 'LEFT'
            elif key2 == b'H': return 'UP'
            elif key2 == b'P': return 'DOWN'
        return key.decode('utf-8', errors='ignore')
    except ImportError:
        # Unix/Linux/Raspberry Pi
        import tty
        import termios
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        tty.setraw(fd)
        ch = sys.stdin.read(1)
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
        return ch

# Hardware control functions (matching your robot.py)
def set_pulse_us(channel, pulse_us):
    """Set servo pulse width in microseconds"""
    if HARDWARE_AVAILABLE:
        ticks_per_us = 4096 / 20_000
        tick_count = int(pulse_us * ticks_per_us)
        pca.channels[channel].duty_cycle = int(tick_count * 0xFFFF / 4096)
    else:
        print(f"[SIM] Channel {channel}: {pulse_us:.0f}µs pulse")

def write_angle(channel, angle):
    """Map 0–270° to 500–3000 µs (matching your robot.py)"""
    angle = max(0, min(270, angle))
    pulse = 500 + (angle / 270.0) * (3000 - 500)
    set_pulse_us(channel, pulse)

def release_angle(channel):
    """Release servo by setting duty cycle to 0"""
    if HARDWARE_AVAILABLE:
        pca.channels[channel].duty_cycle = 0
    else:
        print(f"[SIM] Released channel {channel}")

# Updated servo mapping to match your robot.py
servo_map = {
    "left_wrist": 0,
    "left_shoulder": 1,
    "left_chest": 2,
    "left_leg1": 3,
    "left_leg2": 4,
    "left_leg3": 5,
    "left_leg4": 6,
    "left_leg5": 7,
    "right_wrist": 8,        # Updated to match robot.py
    "right_shoulder": 9,     # Updated to match robot.py
    "right_chest": 10,       # Updated to match robot.py
    "right_leg1": 11,        # Updated to match robot.py
    "right_leg2": 12,        # Updated to match robot.py
    "right_leg3": 13,        # Updated to match robot.py
    "right_leg4": 14,        # Updated to match robot.py
    "right_leg5": 15,        # Updated to match robot.py
}

calibrated = {}  # will hold your saved angles

def print_instructions():
    """Print detailed calibration instructions"""
    print("=" * 80)
    print("🤖 ENHANCED SERVO CALIBRATION TOOL")
    print("=" * 80)
    print("📋 CONTROLS:")
    print("  ← → Arrow Keys     = Adjust angle by ±1°")
    print("  A / D Keys         = Adjust angle by ±5° (fine adjustment)")
    print("  Q / E Keys         = Adjust angle by ±10° (coarse adjustment)")
    print("  W / S Keys         = Adjust angle by ±20° (very coarse)")
    print("  S Key              = Save current angle and move to next servo")
    print("  N Key              = Skip this servo (don't save)")
    print("  R Key              = Reset to default angle (135°)")
    print("  X Key              = Emergency exit")
    print()
    print("🎯 GOAL: Find the 'neutral' or 'home' position for each servo")
    print("💾 Results will be saved to 'servo_calibration.json'")
    print("⚠️  Servo range: 0° to 270° (will be clamped automatically)")
    hardware_status = "with real hardware" if HARDWARE_AVAILABLE else "in simulation mode"
    print(f"🔧 Running {hardware_status}")
    print("=" * 80)

def calibrate(part):
    chan = servo_map[part]
    angle = 135  # Start at middle position
    
    print(f"\n🔧 Calibrating: {part} (Channel {chan})")
    print("Find the neutral/home position for this servo")
    print("Controls: ←/→ = ±1°, A/D = ±5°, Q/E = ±10°, W/S = ±20°")
    print("Commands: S = Save & Next, N = Skip, R = Reset to 135°, X = Exit")
    
    while True:
        try:
            write_angle(chan, angle)
            # Enhanced status display
            hardware_indicator = "✅" if HARDWARE_AVAILABLE else "🔲"
            angle_bar = "█" * int(angle / 10) + "░" * (27 - int(angle / 10))
            print(f"\r  {hardware_indicator} {part:15s}: {angle:3d}° [{angle_bar}]  ", end="", flush=True)
            
        except Exception as e:
            print(f"\r  ❌ {part:15s}: {angle:3d}° (ERROR: {e})  ", end="", flush=True)

        key = getch()
        
        # Handle different input types
        if key == 'LEFT' or (key == '\x1b' and getch() == '[' and getch() == 'D'):
            # Left arrow - decrease by 1°
            angle = max(0, angle - 1)
        elif key == 'RIGHT' or (key == '\x1b' and getch() == '[' and getch() == 'C'):
            # Right arrow - increase by 1°
            angle = min(270, angle + 1)
        elif key == '\x1b':  # Handle escape sequences
            key2 = getch()
            if key2:
                key3 = getch()
                if key3 == 'C':   # Right arrow
                    angle = min(270, angle + 1)
                elif key3 == 'D': # Left arrow
                    angle = max(0, angle - 1)
        elif key.lower() == 'a':  # Fine adjustment left
            angle = max(0, angle - 5)
        elif key.lower() == 'd':  # Fine adjustment right
            angle = min(270, angle + 5)
        elif key.lower() == 'q':  # Coarse adjustment left
            angle = max(0, angle - 10)
        elif key.lower() == 'e':  # Coarse adjustment right
            angle = min(270, angle + 10)
        elif key.lower() == 'w':  # Very coarse adjustment up
            angle = min(270, angle + 20)
        elif key.lower() == 's' and key != 's':  # Very coarse adjustment down (not save)
            angle = max(0, angle - 20)
        elif key == 's':  # Save (capital S)
            calibrated[part] = angle
            print(f"\n ✅ Saved {part} = {angle}°")
            break
        elif key.lower() == 'n':  # Skip this servo
            print(f"\n ⏭️  Skipped {part} (not saved)")
            break
        elif key.lower() == 'r':  # Reset to default
            angle = 135
            print(f"\n 🔄 Reset {part} to {angle}°")
        elif key.lower() == 'x':  # Emergency exit
            print("\n❌ Emergency exit - calibration stopped.")
            sys.exit(0)

def release_all_servos():
    """Release all servo motors"""
    print("🔄 Releasing all servos...")
    for i in range(16):
        release_angle(i)
    status = "released" if HARDWARE_AVAILABLE else "simulated release"
    print(f"✅ All 16 servos {status}")

def load_existing_calibration():
    """Load existing calibration if available"""
    if os.path.exists("servo_calibration.json"):
        try:
            with open("servo_calibration.json", "r") as f:
                existing = json.load(f)
            print(f"📂 Found existing calibration with {len(existing)} servos")
            
            response = input("Load existing values as starting points? (y/n): ").lower()
            if response == 'y':
                return existing
        except Exception as e:
            print(f"⚠️  Could not load existing calibration: {e}")
    
    return {}

if __name__ == "__main__":
    print_instructions()
    
    # Load existing calibration if available
    existing_calibration = load_existing_calibration()
    
    # Release all motors before calibration
    release_all_servos()
    
    input("\n🚀 Press ENTER to start calibration...")
    
    # Calibrate each servo with progress tracking
    servo_names = list(servo_map.keys())
    total_servos = len(servo_names)
    
    for i, part in enumerate(servo_names):
        print(f"\n📍 Progress: {i+1}/{total_servos} servos")
        
        # Use existing calibration as starting point if available
        if part in existing_calibration:
            print(f"💾 Using existing value {existing_calibration[part]}° as starting point")
        
        calibrate(part)
    
    # Save results with backup
    if calibrated:
        # Create backup of existing file
        if os.path.exists("servo_calibration.json"):
            backup_name = f"servo_calibration_backup_{int(time.time())}.json"
            os.rename("servo_calibration.json", backup_name)
            print(f"📋 Backed up existing calibration to {backup_name}")
        
        # Save new calibration
        with open("servo_calibration.json", "w") as f:
            json.dump(calibrated, f, indent=2, sort_keys=True)
        
        print(f"\n🎉 Calibration complete! {len(calibrated)}/{total_servos} servos calibrated.")
        print("📁 Values saved to 'servo_calibration.json'")
        
        # Show summary
        print("\n📋 CALIBRATION SUMMARY:")
        print("-" * 40)
        for part, angle in sorted(calibrated.items()):
            print(f"  {part:15s}: {angle:3d}°")
        print("-" * 40)
        
        # Show skipped servos
        skipped = set(servo_names) - set(calibrated.keys())
        if skipped:
            print(f"\n⚠️  Skipped servos: {', '.join(sorted(skipped))}")
    else:
        print("\n⚠️  No servos were calibrated.")
    
    # Final cleanup
    release_all_servos()
    print("\n✅ Calibration session complete. Safe to disconnect power.")
    
    input("\nPress ENTER to exit...")