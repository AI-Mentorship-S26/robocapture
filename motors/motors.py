import RPi.GPIO as GPIO
import time

# --- PIN DEFINITIONS ---
# Based on your images and notes:
AIN1 = 17  # Left Motor Direction 1
AIN2 = 27  # Left Motor Direction 2
PWMA = 18  # Left Motor Speed (PWM)

BIN1 = 23  # Right Motor Direction 1 (Example pins, verify your wiring)
BIN2 = 24  # Right Motor Direction 2
PWMB = 19  # Right Motor Speed (PWM)

# --- SETUP ---
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# Set all pins as output
pins = [AIN1, AIN2, PWMA, BIN1, BIN2, PWMB]
for pin in pins:
    GPIO.setup(pin, GPIO.OUT)

# Initialize PWM at 1000Hz (1kHz)
# This creates the "wave" signal you mentioned
pwm_left = GPIO.PWM(PWMA, 1000)
pwm_right = GPIO.PWM(PWMB, 1000)

# Start PWM at 0% speed
pwm_left.start(0)
pwm_right.start(0)

def move_straight(speed):
    """
    Moves both motors forward at the specified speed (0-100)
    """
    # LEFT MOTOR FORWARD logic
    GPIO.output(AIN1, GPIO.HIGH)
    GPIO.output(AIN2, GPIO.LOW)
    
    # RIGHT MOTOR FORWARD logic 
    # (Using the logic from your notes)
    GPIO.output(BIN1, GPIO.HIGH)
    GPIO.output(BIN2, GPIO.LOW)
    
    # Set the Speed (Duty Cycle)
    pwm_left.ChangeDutyCycle(speed)
    pwm_right.ChangeDutyCycle(speed)

try:
    # 60 is a good starting duty cycle (not too fast, not too slow)
    print("Robot moving straight...")
    move_straight(60)
    
    # Run for 5 seconds as a test
    time.sleep(5)

finally:
    # ALWAYS stop the motors and clean up
    # Otherwise they might keep spinning if the script crashes
    print("Stopping motors...")
    pwm_left.stop()
    pwm_right.stop()
    GPIO.cleanup()