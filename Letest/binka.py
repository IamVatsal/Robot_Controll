import adafruit_platformdetect

detector = adafruit_platformdetect.PlatformDetect()

print("Detecting platform...")
print("Board ID:", detector.board.id)
print("Chip ID:", detector.chip.id)
print("OS:", detector.os.id)
