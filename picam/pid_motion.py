"""
pid_motion.py
─────────────
Motion controller built directly from turn_verbose.py internals.
The turn logic is copy-pasted from turn_verbose with no modifications.

Test:
    python3 pid_motion.py --test-turn
    python3 pid_motion.py --test-drive
"""

import pigpio
import time
import argparse

# ══════════════════════════════════════════════════════════════════════════════
#  CONFIG
# ══════════════════════════════════════════════════════════════════════════════

TICKS_FOR_90 = (2605 / 4)   # ← your measured value from turn_verbose.py
TICKS_PER_CM = 40.0    # ← update after drive calibration

SPEED        = 150     # turn speed — must match what TICKS_FOR_90 was measured at
DRIVE_SPEED  = 180     # forward speed

STABILISE_SEC = 0.3

# ── Pins ───────────────────────────────────────────────────────────────────────
AIN1, AIN2, PWMA     = 6,  5,  12
BIN1, BIN2, PWMB     = 16, 26, 13
STBY                 = 25
LEFT_ENC_A, LEFT_ENC_B   = 24, 25
RIGHT_ENC_A, RIGHT_ENC_B = 17, 27

# ══════════════════════════════════════════════════════════════════════════════
#  PIGPIO — copied verbatim from turn_verbose.py
# ══════════════════════════════════════════════════════════════════════════════

pi = pigpio.pi()
if not pi.connected:
    raise RuntimeError("Cannot connect to pigpiod — run 'sudo pigpiod' first.")

for pin in [AIN1, AIN2, PWMA, BIN1, BIN2, PWMB, STBY]:
    pi.set_mode(pin, pigpio.OUTPUT)
pi.set_PWM_range(PWMA, 255);      pi.set_PWM_range(PWMB, 255)
pi.set_PWM_frequency(PWMA, 1000); pi.set_PWM_frequency(PWMB, 1000)
pi.write(STBY, 1)

# ── Encoders — copied verbatim from turn_verbose.py ───────────────────────────
_lookup = [0,-1,1,0, 1,0,0,-1, -1,0,0,1, 0,1,-1,0]
_L, _R  = 0, 0
_LA, _LB, _RA, _RB = 0, 0, 0, 0

def on_left(gpio, level, _t):
    global _L, _LA, _LB
    cA, cB = (level, pi.read(LEFT_ENC_B)) if gpio == LEFT_ENC_A else (pi.read(LEFT_ENC_A), level)
    _L += _lookup[(_LA<<3)|(_LB<<2)|(cA<<1)|cB]
    _LA, _LB = cA, cB

def on_right(gpio, level, _t):
    global _R, _RA, _RB
    cA, cB = (level, pi.read(RIGHT_ENC_B)) if gpio == RIGHT_ENC_A else (pi.read(RIGHT_ENC_A), level)
    _R += _lookup[(_RA<<3)|(_RB<<2)|(cA<<1)|cB]
    _RA, _RB = cA, cB

for pin in [LEFT_ENC_A, LEFT_ENC_B, RIGHT_ENC_A, RIGHT_ENC_B]:
    pi.set_mode(pin, pigpio.INPUT)
    pi.set_pull_up_down(pin, pigpio.PUD_UP)
    pi.set_glitch_filter(pin, 5)

time.sleep(0.01)
_LA = pi.read(LEFT_ENC_A);  _LB = pi.read(LEFT_ENC_B)
_RA = pi.read(RIGHT_ENC_A); _RB = pi.read(RIGHT_ENC_B)

pi.callback(LEFT_ENC_A,  pigpio.EITHER_EDGE, on_left)
pi.callback(LEFT_ENC_B,  pigpio.EITHER_EDGE, on_left)
pi.callback(RIGHT_ENC_A, pigpio.EITHER_EDGE, on_right)
pi.callback(RIGHT_ENC_B, pigpio.EITHER_EDGE, on_right)

# ── Instant motor kill — verbatim from turn_verbose.py finally block ───────────
def _kill_motors():
    pi.set_PWM_dutycycle(PWMA, 0)
    pi.set_PWM_dutycycle(PWMB, 0)
    pi.write(AIN1, 0); pi.write(AIN2, 0)
    pi.write(BIN1, 0); pi.write(BIN2, 0)

# ══════════════════════════════════════════════════════════════════════════════
#  TURN — verbatim loop from turn_verbose.py
# ══════════════════════════════════════════════════════════════════════════════

def _do_turn():
    L0 = _L

    # Start motors — verbatim from turn_verbose.py
    pi.write(AIN1, 1); pi.write(AIN2, 0)
    pi.set_PWM_dutycycle(PWMA, SPEED)
    pi.write(BIN1, 0); pi.write(BIN2, 1)
    pi.set_PWM_dutycycle(PWMB, SPEED)

    # Loop — verbatim from turn_verbose.py (minus the prints)
    try:
        while True:
            time.sleep(0.1)
            L = abs(_L - L0)
            R = abs(_R - L0)   # R unused but kept for parity
            avg = L            # only left encoder reliable
            if avg >= TICKS_FOR_90:
                break
    finally:
        # Kill — verbatim from turn_verbose.py finally block
        _kill_motors()

    time.sleep(STABILISE_SEC)


def turn_left_90():
    print("  [Turn] 90°")
    _do_turn()


def turn_right_90():
    """Right turn = three left turns."""
    print("  [Turn] right 90° (3× left)")
    for i in range(3):
        print(f"    step {i+1}/3")
        _do_turn()


# ══════════════════════════════════════════════════════════════════════════════
#  DRIVE FORWARD
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
    L0 = _L

    print(f"  [Drive] {distance_cm:.1f}cm ({int(target_ticks)} ticks)")

    pi.write(AIN1, 1); pi.write(AIN2, 0)
    pi.set_PWM_dutycycle(PWMA, DRIVE_SPEED)
    pi.write(BIN1, 1); pi.write(BIN2, 0)
    pi.set_PWM_dutycycle(PWMB, DRIVE_SPEED)

    try:
        while True:
            time.sleep(0.05)
            if abs(_L - L0) >= target_ticks:
                break
    finally:
        _kill_motors()

    actual_cm = abs(_L - L0) / TICKS_PER_CM
    _total_distance_cm += actual_cm
    print(f"  [Drive] done  actual={actual_cm:.2f}cm  total={_total_distance_cm:.2f}cm")
    time.sleep(STABILISE_SEC)


def drive_forward(duration_sec: float = 1.5):
    """Shim for robot_rl_nav.py — converts seconds to cm."""
    drive_forward_cm(duration_sec * 25.0)


# ══════════════════════════════════════════════════════════════════════════════
#  TESTS
# ══════════════════════════════════════════════════════════════════════════════

def test_turn():
    print(f"Testing 90° turn  (TICKS_FOR_90={TICKS_FOR_90}  PWM={SPEED})")
    L0 = _L
    turn_left_90()
    print(f"  Ticks moved: {abs(_L - L0)}  (target {TICKS_FOR_90})")

def test_drive():
    print("Testing 30cm forward drive")
    drive_forward_cm(30.0)
    print(f"  Odometer: {get_total_distance_cm():.2f}cm")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--test-turn",  action="store_true")
    parser.add_argument("--test-drive", action="store_true")
    args = parser.parse_args()

    try:
        if args.test_turn:
            test_turn()
        elif args.test_drive:
            test_drive()
        else:
            parser.print_help()
    finally:
        _kill_motors()
        pi.write(STBY, 0)
        pi.stop()
