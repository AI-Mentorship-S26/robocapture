import pigpio
import time

# --- PIN DEFINITIONS (BCM Numbering) ---
# Left Motor
AIN1, AIN2, PWMA = 17, 27, 18
# Right Motor
BIN1, BIN2, PWMB = 23, 24, 19
# Standby Pin (Important!)
STBY = 9

# Initialize pigpio
pi = pigpio.pi()

# --- SETUP ---
pins = [AIN1, AIN2, PWMA, BIN1, BIN2, PWMB, STBY]
for pin in pins:
    pi.set_mode(pin, pigpio.OUTPUT)

# Enable the motor driver
pi.write(STBY, 1)

def set_motors(left_speed, right_speed):
    """
    Controls speed and direction. 
    Range: -255 (Full Reverse) to 255 (Full Forward)
    """
    # Left Motor Logic
    if left_speed >= 0:
        pi.write(AIN1, 1); pi.write(AIN2, 0)
        pi.set_PWM_dutycycle(PWMA, left_speed)
    else:
        pi.write(AIN1, 0); pi.write(AIN2, 1)
        pi.set_PWM_dutycycle(PWMA, abs(left_speed))

    # Right Motor Logic
    if right_speed >= 0:
        pi.write(BIN1, 1); pi.write(BIN2, 0)
        pi.set_PWM_dutycycle(PWMB, right_speed)
    else:
        pi.write(BIN1, 0); pi.write(BIN2, 1)
        pi.set_PWM_dutycycle(PWMB, abs(right_speed))

# --- MAIN LOOP ---
try:
    print("Moving Forward...")
    set_motors(200, 200)
    time.sleep(2)

    print("Spinning Right...")
    set_motors(150, -150)
    time.sleep(1)

    print("Stopping...")
    set_motors(0, 0)

finally:
    # This block runs even if you press Ctrl+C or the code crashes
    pi.write(STBY, 0)      # Disable driver
    pi.set_PWM_dutycycle(PWMA, 0)
    pi.set_PWM_dutycycle(PWMB, 0)
    pi.stop()              # Disconnect from daemon
    print("Robot safely disarmed.")