# Bipedal Robot Control System with ML, Voice, and Emotions

This repository contains all the code and tools to control a 16-servo bipedal humanoid robot using a Raspberry Pi. The robot can walk, show expressive emotions on a digital face, and interact with users via voice using machine learning (ML) and AI APIs.

## Features

- **Bipedal Walking**: Smooth, realistic walking using coordinated servo control (MG996R servos + PCA9685 controller)
- **Voice Assistant**: Talk to the robot and get spoken responses using AI/ML APIs
- **Emotional Expressions**: Robot face displays a wide range of emotions and animations
- **Calibration Tools**: Easy servo calibration and configuration
- **Cross-Platform**: Develop on Windows, deploy on Raspberry Pi
- **Modular Code**: Easy to extend for new behaviors or hardware

## Hardware Requirements

- Raspberry Pi (any model with I2C support)
- PCA9685 16-channel PWM servo controller
- 16x MG996R (or compatible) servos
- Microphone and speaker (for voice interaction)
- Display (for robot face/emotions)

## Software Requirements

- Python 3.7+
- Libraries: `adafruit-circuitpython-pca9685`, `adafruit-blinka`, `pygame`, `PyOpenGL`, `requests`, `pyaudio`, etc.
- See `requirements.txt` for full list

## Main Components

- `robot/robot.py` - Main robot control class (walking, gestures, keyboard control)
- `robot/Calibrate.py` - Servo calibration tool
- `talk.py` - Voice assistant and emotion display system
- `enhanced_expressions.json` - Config for robot face expressions

## Usage

### 1. Calibrate Servos
```
python robot/Calibrate.py
```
Follow on-screen instructions to calibrate each servo and save `servo_calibration.json`.

### 2. Control the Robot
```
python robot/robot.py
```
- Use keyboard to walk, wave, or manually control joints.
- Press `w` for walking demo, `h` for hi gesture, `k` for manual control.

### 3. Run Voice Assistant & Emotions
```
python mtalk.py
```
- Robot will listen, talk, and show emotions on the display.

## Project Structure

```
robot/
  robot.py           # Main robot control
  Calibrate.py       # Servo calibration
  ...
talk.py              # Voice/emotion system
enhanced_expressions.json
servo_calibration.json
```

## Customization
- Edit `enhanced_expressions.json` to add or modify facial expressions
- Tweak walking parameters in `robot.py` for your robot's mechanics

## Credits
- Built with Adafruit CircuitPython libraries
- Uses OpenAI/ML APIs for voice and conversation

## License
MIT License
