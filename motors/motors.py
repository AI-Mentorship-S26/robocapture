import pigpio
import time

# --- PIN DEFINITIONS (BCM Numbering) ---
# Left Motor
AIN1, AIN2, PWMA = 17, 27, 18
# Right Motor
BIN1, BIN2, PWMB = 23, 24, 19
# Standby Pin — NOTE: GPIO 9 is SPI0_MISO; if SPI is enabled, use a different pin (e.g. GPIO 25)
STBY = 25

# Initialize pigpio
pi = pigpio.pi()

# --- CRITICAL: Verify connection to pigpiod daemon ---
if not pi.connected:
    raise RuntimeError(
        "Cannot connect to pigpiod daemon!\n"
        "Fix: run 'sudo pigpiod' on the Raspberry Pi before executing this script."
    )

print("Connected to pigpiod OK.")

# --- SETUP ---
pins = [AIN1, AIN2, PWMA, BIN1, BIN2, PWMB, STBY]
for pin in pins:
    pi.set_mode(pin, pigpio.OUTPUT)

# Set explicit PWM range (0–255) and frequency (1kHz) for both motor PWM pins
pi.set_PWM_range(PWMA, 255)
pi.set_PWM_range(PWMB, 255)
pi.set_PWM_frequency(PWMA, 1000)
pi.set_PWM_frequency(PWMB, 1000)

# Enable the motor driver (STBY HIGH = active)
pi.write(STBY, 1)
print(f"STBY (GPIO {STBY}) set HIGH — motor driver enabled.")


def set_motors(left_speed, right_speed):
    """
    Controls speed and direction.
    Range: -255 (Full Reverse) to 255 (Full Forward)
    Values are clamped to [-255, 255].
    """
    left_speed  = max(-255, min(255, left_speed))
    right_speed = max(-255, min(255, right_speed))

    # Left Motor Logic
    if left_speed >= 0:
        pi.write(AIN1, 1)
        pi.write(AIN2, 0)
        pi.set_PWM_dutycycle(PWMA, left_speed)
    else:
        pi.write(AIN1, 0)
        pi.write(AIN2, 1)
        pi.set_PWM_dutycycle(PWMA, abs(left_speed))

    # Right Motor Logic
    if right_speed >= 0:
        pi.write(BIN1, 1)
        pi.write(BIN2, 0)
        pi.set_PWM_dutycycle(PWMB, right_speed)
    else:
        pi.write(BIN1, 0)
        pi.write(BIN2, 1)
        pi.set_PWM_dutycycle(PWMB, abs(right_speed))

    print(f"  Motors set → Left: {left_speed}, Right: {right_speed}")


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
    time.sleep(0.5)   # Brief pause before cleanup

finally:
    # Runs even on Ctrl+C or crash — always disarm safely
    pi.write(STBY, 0)
    pi.set_PWM_dutycycle(PWMA, 0)
    pi.set_PWM_dutycycle(PWMB, 0)
    pi.stop()
    print("Robot safely disarmed.")
