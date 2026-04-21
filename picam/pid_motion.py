"""
pid_motion.py
─────────────
Encoder-based PID motion controller — LEFT TURNS ONLY.
Only uses the left encoder (right encoder not required).

Test a 90° left turn:
    python3 pid_motion.py --test-turn

Test a 30 cm drive:
    python3 pid_motion.py --test-drive
"""

import time
import argparse
import math
import pigpio

# ══════════════════════════════════════════════════════════════════════════════
#  CONFIGURATION
# ══════════════════════════════════════════════════════════════════════════════

# ── Measured values — paste yours here ────────────────────────────────────────
TICKS_FOR_90 = 2600     # ← ticks the LEFT encoder counts during a 90° left turn
TICKS_PER_CM = 40.0     # ← left encoder ticks per cm of forward travel
                         #   (measure by driving a known distance)

# ── Motor pins ─────────────────────────────────────────────────────────────────
AIN1, AIN2, PWMA = 6,  5,  12   # left motor
BIN1, BIN2, PWMB = 16, 26, 13   # right motor
STBY             = 25

# ── Left encoder pins only ─────────────────────────────────────────────────────
LEFT_ENC_A = 24
LEFT_ENC_B = 25

# ── Turn speed — keep at whatever speed you measured TICKS_FOR_90 at ──────────
TURN_SPEED = 150        # PWM 0-255
TURN_SETTLE_TICKS  = 15  # stop when error within this many ticks
TURN_SETTLE_CYCLES = 3   # for this many consecutive cycles

# ── Drive PID gains ────────────────────────────────────────────────────────────
DRIVE_BASE_SPEED = 180
DRIVE_MIN_SPEED  = 80
DRIVE_MAX_SPEED  = 230
DRIVE_KP = 0.0          # steering PID disabled (no right encoder to compare)
DRIVE_KI = 0.0
DRIVE_KD = 0.0

# ── Timing ─────────────────────────────────────────────────────────────────────
LOOP_INTERVAL = 0.1     # seconds between tick checks (match turn_verbose.py)
STABILISE_SEC = 0.3

# ══════════════════════════════════════════════════════════════════════════════
#  PIGPIO + ENCODER SETUP  (single instance, left encoder only)
# ══════════════════════════════════════════════════════════════════════════════

pi = pigpio.pi()
if not pi.connected:
    raise RuntimeError("Cannot connect to pigpiod — run 'sudo pigpiod' first.")

# Motor pins
for pin in [AIN1, AIN2, PWMA, BIN1, BIN2, PWMB, STBY]:
    pi.set_mode(pin, pigpio.OUTPUT)
pi.set_PWM_range(PWMA, 255);        pi.set_PWM_range(PWMB, 255)
pi.set_PWM_frequency(PWMA, 1000);   pi.set_PWM_frequency(PWMB, 1000)
pi.write(STBY, 1)

# Left encoder state
_lookup = [0,-1,1,0, 1,0,0,-1, -1,0,0,1, 0,1,-1,0]
_L      = 0
_LA, _LB = 0, 0

def _on_left(gpio, level, _t):
    global _L, _LA, _LB
    if gpio == LEFT_ENC_A:
        cA, cB = level, pi.read(LEFT_ENC_B)
    else:
        cA, cB = pi.read(LEFT_ENC_A), level
    _L += _lookup[(_LA<<3)|(_LB<<2)|(cA<<1)|cB]
    _LA, _LB = cA, cB

for pin in [LEFT_ENC_A, LEFT_ENC_B]:
    pi.set_mode(pin, pigpio.INPUT)
    pi.set_pull_up_down(pin, pigpio.PUD_UP)
    pi.set_glitch_filter(pin, 5)

time.sleep(0.01)
_LA = pi.read(LEFT_ENC_A)
_LB = pi.read(LEFT_ENC_B)

pi.callback(LEFT_ENC_A, pigpio.EITHER_EDGE, _on_left)
pi.callback(LEFT_ENC_B, pigpio.EITHER_EDGE, _on_left)

def _get_left(): return _L

# ══════════════════════════════════════════════════════════════════════════════
#  MOTOR HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _set_motors(left_pwm: int, right_pwm: int):
    left_pwm  = max(-255, min(255, left_pwm))
    right_pwm = max(-255, min(255, right_pwm))
    if left_pwm >= 0:
        pi.write(AIN1, 1); pi.write(AIN2, 0)
        pi.set_PWM_dutycycle(PWMA, left_pwm)
    else:
        pi.write(AIN1, 0); pi.write(AIN2, 1)
        pi.set_PWM_dutycycle(PWMA, abs(left_pwm))
    if right_pwm >= 0:
        pi.write(BIN1, 1); pi.write(BIN2, 0)
        pi.set_PWM_dutycycle(PWMB, right_pwm)
    else:
        pi.write(BIN1, 0); pi.write(BIN2, 1)
        pi.set_PWM_dutycycle(PWMB, abs(right_pwm))

def _stop_motors(coast_sec: float = STABILISE_SEC):
    _set_motors(0, 0)
    time.sleep(coast_sec)

# ══════════════════════════════════════════════════════════════════════════════
#  TURN LEFT  (left wheel back, right wheel forward)
# ══════════════════════════════════════════════════════════════════════════════

def _turn_left_steps(steps: int):
    """Execute `steps` × 90° left turns back-to-back."""
    for i in range(steps):
        print(f"  [Turn] left 90° ({i+1}/{steps})")
        L0           = _get_left()
        settle_count = 0

        # Left wheel reverse, right wheel forward
        _set_motors(-TURN_SPEED, TURN_SPEED)

        while True:
            time.sleep(LOOP_INTERVAL)
            moved = abs(_get_left() - L0)
            error = TICKS_FOR_90 - moved

            if error <= TURN_SETTLE_TICKS:
                settle_count += 1
                if settle_count >= TURN_SETTLE_CYCLES:
                    print(f"  [Turn] done  ticks={moved}  err={error:.0f}")
                    break
            else:
                settle_count = 0

        _stop_motors()


def turn_left_90():
    """Single 90° left turn."""
    _turn_left_steps(1)


def turn_right_90():
    """
    90° right turn achieved by three 90° left turns.
    Keeps robot_rl_nav.py working with no changes.
    """
    _turn_left_steps(3)


# ══════════════════════════════════════════════════════════════════════════════
#  DRIVE FORWARD  (left encoder only for distance)
# ══════════════════════════════════════════════════════════════════════════════

_total_distance_cm = 0.0

def get_total_distance_cm():
    return _total_distance_cm

def reset_distance():
    global _total_distance_cm
    _total_distance_cm = 0.0


def drive_forward_cm(distance_cm: float):
    global _total_distance_cm
    target_ticks = distance_cm * TICKS_PER_CM
    L0 = _get_left()

    print(f"  [Drive] target={distance_cm:.1f}cm  ({target_ticks:.0f} ticks)")
    _set_motors(DRIVE_BASE_SPEED, DRIVE_BASE_SPEED)

    while True:
        time.sleep(0.05)
        moved = abs(_get_left() - L0)
        if moved >= target_ticks:
            break

    _stop_motors()

    actual_cm = abs(_get_left() - L0) / TICKS_PER_CM
    _total_distance_cm += actual_cm
    print(f"  [Drive] done  actual={actual_cm:.2f}cm  total={_total_distance_cm:.2f}cm")


def drive_forward(duration_sec: float = 1.5):
    """Shim for robot_rl_nav.py which passes a duration — converts to cm."""
    ESTIMATED_CM_PER_SEC = 25.0
    drive_forward_cm(duration_sec * ESTIMATED_CM_PER_SEC)


# ══════════════════════════════════════════════════════════════════════════════
#  STANDALONE TESTS
# ══════════════════════════════════════════════════════════════════════════════

def test_turn():
    print(f"Testing 90° left turn  (TICKS_FOR_90={TICKS_FOR_90})")
    L0 = _get_left()
    turn_left_90()
    print(f"  Left ticks moved: {abs(_get_left()-L0)}  (target {TICKS_FOR_90})")

def test_drive():
    print("Testing 30 cm forward drive")
    drive_forward_cm(30.0)
    print(f"  Odometer: {get_total_distance_cm():.2f} cm")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--test-turn",  action="store_true", help="Test one 90° left turn")
    parser.add_argument("--test-drive", action="store_true", help="Test 30cm forward drive")
    args = parser.parse_args()

    try:
        if args.test_turn:
            test_turn()
        elif args.test_drive:
            test_drive()
        else:
            parser.print_help()
    finally:
        _stop_motors(0)
        pi.write(STBY, 0)
        pi.stop()
