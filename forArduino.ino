#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>

Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver();

#define SERVOMIN  150 // this is the 'minimum' pulse length count (approx 0°)
#define SERVOMAX  600 // this is the 'maximum' pulse length count (approx 180°)

void setup() {
  Serial.begin(9600);
  Serial.println("PCA9685 Servo test");

  pwm.begin();
  pwm.setPWMFreq(50);  // Analog servos run at ~50 Hz

  delay(10);
}

void loop() {
  // Sweep servo on channel 0 from 0 to 180 and back
  for (int pos = SERVOMIN; pos < SERVOMAX; pos++) {
    pwm.setPWM(0, 0, pos);
    delay(5);
  }

  for (int pos = SERVOMAX; pos > SERVOMIN; pos--) {
    pwm.setPWM(0, 0, pos);
    delay(5);
  }
}
