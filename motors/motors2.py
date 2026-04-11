import pigpio
import time
import random
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


# --- COMMAND QUEUE ---
command_queue = deque()

# --- MOVEMENT FUNCTIONS ---
def go_forward(speed=200, duration=0.5):   # duration halved from 1.0
    command_queue.append((speed, speed, duration, f"Forward (speed={speed})"))

def go_backward(speed=200, duration=0.5):
    command_queue.append((-speed, -speed, duration, f"Backward (speed={speed})"))

def turn_left(speed=150, duration=0.9):    # 0.9 fixed as tested
    command_queue.append((-speed, speed, duration, f"Turn Left (speed={speed})"))

def turn_right(speed=150, duration=0.9):   # 0.9 fixed as tested
    command_queue.append((speed, -speed, duration, f"Turn Right (speed={speed})"))

def stop(duration=0.5):
    command_queue.append((0, 0, duration, "Stop"))


# --- RANDOM WALK ---
def random_walk(steps):
    """
    Queues `steps` iterations of: go_forward then a random turn (left or right).
    Turn duration is fixed at 0.9 (tested). Forward duration uses the default (0.5).
    Change the `steps` argument at the call site below — nothing is hard-coded here.
    """
    turns = [turn_left, turn_right]
    for _ in range(steps):
        go_forward()
        random.choice(turns)()


# --- Set your desired number of random steps here ---
NUM_STEPS = 10

random_walk(NUM_STEPS)
stop()


# --- STATE ---
current_cmd = None
cmd_start   = None


# --- MAIN LOOP ---
try:
    print(f"Starting random walk: {NUM_STEPS} steps...")

    while True:
        now = time.monotonic()

        if current_cmd is None:
            if command_queue:
                current_cmd = command_queue.popleft()
                left, right, duration, label = current_cmd
                print(label + "...")
                set_motors(left, right)
                cmd_start = now
        else:
            _, _, duration, _ = current_cmd
            if now - cmd_start >= duration:
                current_cmd = None
                cmd_start   = None

        time.sleep(0.01)  # yields CPU to other Pi processes — do NOT remove

finally:
    pi.write(STBY, 0)
    pi.set_PWM_dutycycle(PWMA, 0)
    pi.set_PWM_dutycycle(PWMB, 0)
    pi.stop()
    print("Robot safely disarmed.")
