#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>

// Two PCA9685 boards with different I2C addresses
Adafruit_PWMServoDriver pwm1 = Adafruit_PWMServoDriver(0x40); // First 16 servos
Adafruit_PWMServoDriver pwm2 = Adafruit_PWMServoDriver(0x41); // 17th servo

#define SERVOMIN 130
#define SERVOMAX 510

int angleToPulse(int angle) {
  return map(angle, 0, 180, SERVOMIN, SERVOMAX);
}

void setup() {
  Serial.begin(9600);

  pwm1.begin();
  pwm1.setPWMFreq(50);

  pwm2.begin();
  pwm2.setPWMFreq(50);
}

void loop() {
  // Set first 16 servos using pwm1
  for (int i = 0; i < 16; i++) {
    pwm1.setPWM(i, 0, angleToPulse(90));
    delay(100);
  }

  // Set 17th servo (channel 0 of second board)
  pwm2.setPWM(0, 0, angleToPulse(90));

  delay(2000);
}
