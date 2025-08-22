# Bipedal Robot Control System with ML, Voice, and Emotions

![Robot waving hand](Robot.gif)

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

- `main/mtalk.py` - Main entry point for running on Raspberry Pi (recommended usage)
- `robot/robot.py` - Robot control class (testing and development)
- `robot/Calibrate.py` - Servo calibration tool
- `talk.py` - Voice assistant and emotion display system
- `enhanced_expressions.json` - Config for robot face expressions

## Usage

### 1. Calibrate Servos
```
python robot/Calibrate.py
```
Follow on-screen instructions to calibrate each servo and save `servo_calibration.json`.

### 2. Run on Raspberry Pi (Recommended)
```
python main/robot.py
```
- This is the main file for controlling the robot on Raspberry Pi.

### 3. Testing and Development
- Files in `robot/` are for testing and development purposes.

### 4. Run Voice Assistant & Emotions
```
python mtalk.py
```
- Robot will listen, talk, and show emotions on the display.

## Project Structure

```
main/                     # Main entry for Raspberry Pi
robot/
  robot.py                # Robot control (testing)
  ...
mtalk.py                  # Voice/emotion system
extra/                    # Old tests and extra things (not needed for main usage)
```

## Customization
- Edit `enhanced_expressions.json` to add or modify facial expressions
- Tweak walking parameters in `robot.py` for your robot's mechanics

## Credits
- Built with Adafruit CircuitPython libraries
- Uses OpenAI/ML APIs for voice and conversation

## License
MIT License
