#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>

Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver();

#define SERVOMIN  150  // PWM value for 0°
#define SERVOMAX  600  // PWM value for 180°

void setup() {
  Serial.begin(9600);
  pwm.begin();
  pwm.setPWMFreq(50);  // standard for analog servos
  delay(10);
}

// Helper to convert angle (0–180) to PWM
int angleToPulse(int angle) {
  return map(angle, 0, 180, SERVOMIN, SERVOMAX);
}

void loop() {
  // Move servo on channel 0 to 90°
  int angle = 90;
  pwm.setPWM(0, 0, angleToPulse(angle));
  delay(2000);

  // Move to 0°
  pwm.setPWM(0, 0, angleToPulse(0));
  delay(2000);

  // Move to 180°
  pwm.setPWM(0, 0, angleToPulse(180));
  delay(2000);
}
