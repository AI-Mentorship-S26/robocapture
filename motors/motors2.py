import pigpio
import time
from collections import deque

# --- PIN DEFINITIONS ---
AIN1, AIN2, PWMA = 6, 5, 12
BIN1, BIN2, PWMB = 16, 26, 13
STBY = 25

# --- Initialize pigpio ---
pi = pigpio.pi()
if not pi.connected:
    raise RuntimeError(
        "Cannot connect to pigpiod daemon!\n"
        "Fix: run 'sudo pigpiod' before executing this script."
    )
print("Connected to pigpiod OK.")

# --- SETUP ---
pins = [AIN1, AIN2, PWMA, BIN1, BIN2, PWMB, STBY]
for pin in pins:
    pi.set_mode(pin, pigpio.OUTPUT)

pi.set_PWM_range(PWMA, 255)
pi.set_PWM_range(PWMB, 255)
pi.set_PWM_frequency(PWMA, 1000)
pi.set_PWM_frequency(PWMB, 1000)

pi.write(STBY, 1)
print(f"STBY (GPIO {STBY}) set HIGH — motor driver enabled.")


# --- LOW-LEVEL MOTOR CONTROL ---
def set_motors(left_speed, right_speed):
    """
    Raw motor control. Range: -255 (full reverse) to 255 (full forward).
    Called only by the main loop — never call directly from movement functions.
    """
    left_speed  = max(-255, min(255, left_speed))
    right_speed = max(-255, min(255, right_speed))

    if left_speed >= 0:
        pi.write(AIN1, 1); pi.write(AIN2, 0)
        pi.set_PWM_dutycycle(PWMA, left_speed)
    else:
        pi.write(AIN1, 0); pi.write(AIN2, 1)
        pi.set_PWM_dutycycle(PWMA, abs(left_speed))

    if right_speed >= 0:
        pi.write(BIN1, 1); pi.write(BIN2, 0)
        pi.set_PWM_dutycycle(PWMB, right_speed)
    else:
        pi.write(BIN1, 0); pi.write(BIN2, 1)
        pi.set_PWM_dutycycle(PWMB, abs(right_speed))

    print(f"  Motors set → Left: {left_speed}, Right: {right_speed}")


# ---------------------------------------------------------------------------
# COMMAND QUEUE
# Movement functions don't block — they just push a command onto the queue.
# The main loop pops and executes them one at a time using elapsed-time checks.
# Format: (left_speed, right_speed, duration, label)
# ---------------------------------------------------------------------------
command_queue = deque()

# --- MOVEMENT FUNCTIONS ---
def go_forward(speed=200, duration=1.0):
    """Queue a forward move. Returns immediately — does not block."""
    command_queue.append((speed, speed, duration, f"Forward (speed={speed})"))

def go_backward(speed=200, duration=1.0):
    """Queue a backward move. Returns immediately — does not block."""
    command_queue.append((-speed, -speed, duration, f"Backward (speed={speed})"))

def turn_left(speed=150, duration=1.0):
    """Queue a left turn (left motor back, right motor forward). Returns immediately."""
    command_queue.append((-speed, speed, duration, f"Turn Left (speed={speed})"))

def turn_right(speed=150, duration=1.0):
    """Queue a right turn (left motor forward, right motor back). Returns immediately."""
    command_queue.append((speed, -speed, duration, f"Turn Right (speed={speed})"))

def stop(duration=0.5):
    """Queue a full stop, held for duration. Returns immediately."""
    command_queue.append((0, 0, duration, "Stop"))


# --- Build your movement plan here ---
# These calls return instantly — they only fill the queue.
go_forward(speed=200, duration=2.0)
turn_right(speed=150, duration=1.0)
go_forward(speed=200, duration=1.5)
turn_left(speed=150, duration=1.0)
stop()

# --- STATE ---
current_cmd = None   # (left, right, duration, label) currently executing
cmd_start   = None   # monotonic timestamp when current command started


# --- MAIN LOOP ---
try:
    print("Starting non-blocking motor control...")

    while True:
        now = time.monotonic()

        # --- Command executor ---
        if current_cmd is None:
            if command_queue:                       # grab the next command
                current_cmd = command_queue.popleft()
                left, right, duration, label = current_cmd
                print(label + "...")
                set_motors(left, right)
                cmd_start = now
            # else: queue empty, motors hold their last state
        else:
            left, right, duration, label = current_cmd
            if now - cmd_start >= duration:         # command duration elapsed
                current_cmd = None
                cmd_start   = None

        time.sleep(0.01)  # yields CPU to other Pi processes — do NOT remove

finally:
    pi.write(STBY, 0)
    pi.set_PWM_dutycycle(PWMA, 0)
    pi.set_PWM_dutycycle(PWMB, 0)
    pi.stop()
    print("Robot safely disarmed.")
