"""
pid_motion.py
─────────────
Encoder-based motion controller using the same logic as turn_verbose.py.
Left encoder only. No PID complexity — just run motors and stop at tick target.

Test a 90° turn:
    python3 pid_motion.py --test-turn

Test a 30 cm drive:
    python3 pid_motion.py --test-drive
"""

import time
import argparse
import pigpio

# ══════════════════════════════════════════════════════════════════════════════
#  CONFIGURATION — paste your measured values here
# ══════════════════════════════════════════════════════════════════════════════

TICKS_FOR_90 = 2605    # ← from turn_verbose.py measurement
TICKS_PER_CM = 40.0    # ← measure by driving a known distance, update later

TURN_SPEED   = 150     # PWM — must match the speed used when measuring TICKS_FOR_90
DRIVE_SPEED  = 180     # PWM for driving forward

STABILISE_SEC = 0.3    # pause after each move

# ── Pins ───────────────────────────────────────────────────────────────────────
AIN1, AIN2, PWMA = 6,  5,  12   # left motor
BIN1, BIN2, PWMB = 16, 26, 13   # right motor
STBY             = 25
LEFT_ENC_A       = 24
LEFT_ENC_B       = 25

# ══════════════════════════════════════════════════════════════════════════════
#  SINGLE PIGPIO INSTANCE
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

# Left encoder
_lookup  = [0,-1,1,0, 1,0,0,-1, -1,0,0,1, 0,1,-1,0]
_L       = 0
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

def _get_left():
    return _L

# ══════════════════════════════════════════════════════════════════════════════
#  RAW MOTOR WRITES — exactly like turn_verbose.py
# ══════════════════════════════════════════════════════════════════════════════

def _motors_turn():
    """Left fwd, right rev — same as turn_verbose.py lines 66-69."""
    pi.write(AIN1, 1); pi.write(AIN2, 0)
    pi.set_PWM_dutycycle(PWMA, TURN_SPEED)
    pi.write(BIN1, 0); pi.write(BIN2, 1)
    pi.set_PWM_dutycycle(PWMB, TURN_SPEED)

def _motors_forward():
    pi.write(AIN1, 1); pi.write(AIN2, 0)
    pi.set_PWM_dutycycle(PWMA, DRIVE_SPEED)
    pi.write(BIN1, 1); pi.write(BIN2, 0)
    pi.set_PWM_dutycycle(PWMB, DRIVE_SPEED)

def _motors_stop(coast_sec: float = STABILISE_SEC):
    pi.set_PWM_dutycycle(PWMA, 0)
    pi.set_PWM_dutycycle(PWMB, 0)
    pi.write(AIN1, 0); pi.write(AIN2, 0)
    pi.write(BIN1, 0); pi.write(BIN2, 0)
    time.sleep(coast_sec)

# ══════════════════════════════════════════════════════════════════════════════
#  TURN  — same tick-watch loop as turn_verbose.py
# ══════════════════════════════════════════════════════════════════════════════

def _do_turn():
    """Single 90° turn using exact turn_verbose.py logic."""
    L0 = _get_left()
    _motors_turn()
    while True:
        time.sleep(0.01)
        moved = abs(_get_left() - L0)
        if moved >= TICKS_FOR_90:
            break
    _motors_stop()


def turn_left_90():
    print("  [Turn] 90°")
    _do_turn()


def turn_right_90():
    """Right turn = three left turns."""
    print("  [Turn] right 90° (3× left)")
    for i in range(3):
        print(f"    left turn {i+1}/3")
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
    L0 = _get_left()

    print(f"  [Drive] {distance_cm:.1f}cm ({target_ticks:.0f} ticks)")
    _motors_forward()

    while True:
        time.sleep(0.05)
        if abs(_get_left() - L0) >= target_ticks:
            break

    _motors_stop()
    actual_cm = abs(_get_left() - L0) / TICKS_PER_CM
    _total_distance_cm += actual_cm
    print(f"  [Drive] done  actual={actual_cm:.2f}cm  total={_total_distance_cm:.2f}cm")


def drive_forward(duration_sec: float = 1.5):
    """Shim for robot_rl_nav.py — converts seconds to cm estimate."""
    ESTIMATED_CM_PER_SEC = 25.0
    drive_forward_cm(duration_sec * ESTIMATED_CM_PER_SEC)

# ══════════════════════════════════════════════════════════════════════════════
#  STANDALONE TESTS
# ══════════════════════════════════════════════════════════════════════════════

def test_turn():
    print(f"Testing 90° turn  (TICKS_FOR_90={TICKS_FOR_90}  PWM={TURN_SPEED})")
    L0 = _get_left()
    turn_left_90()
    print(f"  Ticks moved: {abs(_get_left()-L0)}  (target {TICKS_FOR_90})")

def test_drive():
    print("Testing 30cm forward drive")
    drive_forward_cm(30.0)
    print(f"  Odometer: {get_total_distance_cm():.2f}cm")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--test-turn",  action="store_true", help="Test one 90° turn")
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
        _motors_stop(0)
        pi.write(STBY, 0)
        pi.stop()
