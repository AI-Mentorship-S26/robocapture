"""
pid_motion.py
─────────────
Encoder-based PID motion controller for your differential-drive robot.
Does NOT import encodersFull.py — manages its own single pigpio instance
to avoid the dual-daemon conflict.

Test a 90° turn:
    python3 pid_motion.py --test-turn

Test a 30 cm drive:
    python3 pid_motion.py --test-drive
"""

import time
import argparse
import math
import pigpio

# ══════════════════════════════════════════════════════════════════════════════
#  CONFIGURATION  — fill in after calibration
# ══════════════════════════════════════════════════════════════════════════════

TICKS_PER_REV     = 2920     # ← paste your measured value here
WHEEL_DIAMETER_CM = 6.7     # measure across the outside of your wheel (cm)
WHEELBASE_CM      = 23.0    # centre-to-centre between wheels (cm)

# ── Motor pins ─────────────────────────────────────────────────────────────────
AIN1, AIN2, PWMA = 6,  5,  12   # left motor
BIN1, BIN2, PWMB = 16, 26, 13   # right motor
STBY             = 25

# ── Encoder pins ───────────────────────────────────────────────────────────────
LEFT_ENC_A,  LEFT_ENC_B  = 24, 25
RIGHT_ENC_A, RIGHT_ENC_B = 17, 27

# ── PID gains — TURNING ────────────────────────────────────────────────────────
TURN_KP = 2.5
TURN_KI = 0.004
TURN_KD = 0.8

TURN_BASE_SPEED    = 150
TURN_MIN_SPEED     = 150
TURN_MAX_SPEED     = 150
TURN_SETTLE_TICKS  = 3
TURN_SETTLE_CYCLES = 5

# ── PID gains — DRIVING ────────────────────────────────────────────────────────
DRIVE_KP = 1.8
DRIVE_KI = 0.002
DRIVE_KD = 0.5

DRIVE_BASE_SPEED = 180
DRIVE_MIN_SPEED  = 80
DRIVE_MAX_SPEED  = 230

# ── Timing ─────────────────────────────────────────────────────────────────────
PID_LOOP_HZ  = 50
PID_DT       = 1.0 / PID_LOOP_HZ
STABILISE_SEC = 0.3

# ══════════════════════════════════════════════════════════════════════════════
#  DERIVED CONSTANTS
# ══════════════════════════════════════════════════════════════════════════════

WHEEL_CIRC_CM = math.pi * WHEEL_DIAMETER_CM
TICKS_PER_CM  = TICKS_PER_REV / WHEEL_CIRC_CM
TICKS_FOR_90  = 2605

# ══════════════════════════════════════════════════════════════════════════════
#  SINGLE PIGPIO INSTANCE + INLINE ENCODER SETUP
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

# Encoder state
_lookup = [0,-1,1,0, 1,0,0,-1, -1,0,0,1, 0,1,-1,0]

_L_tick  = 0
_L_prevA = 0
_L_prevB = 0

_R_tick  = 0
_R_prevA = 0
_R_prevB = 0

def _on_left(gpio, level, _t):
    global _L_tick, _L_prevA, _L_prevB
    if gpio == LEFT_ENC_A:
        cA, cB = level, pi.read(LEFT_ENC_B)
    else:
        cA, cB = pi.read(LEFT_ENC_A), level
    _L_tick += _lookup[(_L_prevA<<3)|(_L_prevB<<2)|(cA<<1)|cB]
    _L_prevA, _L_prevB = cA, cB

def _on_right(gpio, level, _t):
    global _R_tick, _R_prevA, _R_prevB
    if gpio == RIGHT_ENC_A:
        cA, cB = level, pi.read(RIGHT_ENC_B)
    else:
        cA, cB = pi.read(RIGHT_ENC_A), level
    _R_tick += _lookup[(_R_prevA<<3)|(_R_prevB<<2)|(cA<<1)|cB]
    _R_prevA, _R_prevB = cA, cB

# Encoder pins
for pin in [LEFT_ENC_A, LEFT_ENC_B, RIGHT_ENC_A, RIGHT_ENC_B]:
    pi.set_mode(pin, pigpio.INPUT)
    pi.set_pull_up_down(pin, pigpio.PUD_UP)
    pi.set_glitch_filter(pin, 5)

time.sleep(0.01)
_L_prevA = pi.read(LEFT_ENC_A);  _L_prevB = pi.read(LEFT_ENC_B)
_R_prevA = pi.read(RIGHT_ENC_A); _R_prevB = pi.read(RIGHT_ENC_B)

pi.callback(LEFT_ENC_A,  pigpio.EITHER_EDGE, _on_left)
pi.callback(LEFT_ENC_B,  pigpio.EITHER_EDGE, _on_left)
pi.callback(RIGHT_ENC_A, pigpio.EITHER_EDGE, _on_right)
pi.callback(RIGHT_ENC_B, pigpio.EITHER_EDGE, _on_right)

def _get_left():  return _L_tick
def _get_right(): return _R_tick

# ══════════════════════════════════════════════════════════════════════════════
#  LOW-LEVEL MOTOR HELPERS
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

def _clamp(value, lo, hi):
    return max(lo, min(hi, value))

# ══════════════════════════════════════════════════════════════════════════════
#  PID
# ══════════════════════════════════════════════════════════════════════════════

class _PID:
    def __init__(self, kp, ki, kd):
        self.kp, self.ki, self.kd = kp, ki, kd
        self.integral   = 0.0
        self.prev_error = 0.0

    def compute(self, error, dt):
        self.integral  += error * dt
        derivative      = (error - self.prev_error) / dt if dt > 0 else 0.0
        self.prev_error = error
        return self.kp * error + self.ki * self.integral + self.kd * derivative

# ══════════════════════════════════════════════════════════════════════════════
#  TURN
# ══════════════════════════════════════════════════════════════════════════════

def _turn(direction: int, target_ticks: int = None):
    if target_ticks is None:
        target_ticks = TICKS_FOR_90

    L0 = _get_left()
    R0 = _get_right()

    pid          = _PID(TURN_KP, TURN_KI, TURN_KD)
    settle_count = 0
    last_time    = time.monotonic()

    print(f"  [PID Turn] {'right' if direction>0 else 'left'}  target={target_ticks} ticks")

    while True:
        now = time.monotonic()
        dt  = now - last_time
        if dt < PID_DT:
            time.sleep(PID_DT - dt)
            continue
        last_time = now

        L_moved = abs(_get_left()  - L0)
        R_moved = abs(_get_right() - R0)
        avg_moved = (L_moved + R_moved) / 2.0

        error = target_ticks - avg_moved

        if abs(error) <= TURN_SETTLE_TICKS:
            settle_count += 1
            if settle_count >= TURN_SETTLE_CYCLES:
                print(f"  [PID Turn] done  L={L_moved}  R={R_moved}  err={error:.1f}")
                break
        else:
            settle_count = 0

        output    = pid.compute(error, dt)
        base      = _clamp(abs(output), TURN_MIN_SPEED, TURN_MAX_SPEED)
        imbalance = (L_moved - R_moved) * 0.3
        left_pwm  = _clamp(base - imbalance, TURN_MIN_SPEED, TURN_MAX_SPEED)
        right_pwm = _clamp(base + imbalance, TURN_MIN_SPEED, TURN_MAX_SPEED)

        _set_motors(
            int( direction * left_pwm),
            int(-direction * right_pwm)
        )

    _stop_motors()


def turn_right_90():
    _turn(direction=+1)

def turn_left_90():
    _turn(direction=-1)

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
    R0 = _get_right()

    pid       = _PID(DRIVE_KP, DRIVE_KI, DRIVE_KD)
    last_time = time.monotonic()

    print(f"  [PID Drive] target={distance_cm:.1f}cm  ({target_ticks:.0f} ticks)")

    while True:
        now = time.monotonic()
        dt  = now - last_time
        if dt < PID_DT:
            time.sleep(PID_DT - dt)
            continue
        last_time = now

        L_moved   = _get_left()  - L0
        R_moved   = _get_right() - R0
        avg_moved = (L_moved + R_moved) / 2.0

        if avg_moved >= target_ticks:
            break

        steer_error = L_moved - R_moved
        steer_corr  = pid.compute(steer_error, dt)

        progress = avg_moved / target_ticks if target_ticks > 0 else 1.0
        if progress > 0.8:
            ramp   = 1.0 - ((progress - 0.8) / 0.2)
            speed  = DRIVE_MIN_SPEED + ramp * (DRIVE_BASE_SPEED - DRIVE_MIN_SPEED)
        else:
            speed  = DRIVE_BASE_SPEED

        left_pwm  = _clamp(speed - steer_corr, DRIVE_MIN_SPEED, DRIVE_MAX_SPEED)
        right_pwm = _clamp(speed + steer_corr, DRIVE_MIN_SPEED, DRIVE_MAX_SPEED)
        _set_motors(int(left_pwm), int(right_pwm))

    _stop_motors()

    L_final  = abs(_get_left()  - L0)
    R_final  = abs(_get_right() - R0)
    actual_cm = ((L_final + R_final) / 2.0) / TICKS_PER_CM
    _total_distance_cm += actual_cm
    print(f"  [PID Drive] done  actual={actual_cm:.2f}cm  total={_total_distance_cm:.2f}cm")


def drive_forward(duration_sec: float = 1.5):
    """Shim for robot_rl_nav.py which passes a duration — converts to cm."""
    ESTIMATED_CM_PER_SEC = 25.0
    drive_forward_cm(duration_sec * ESTIMATED_CM_PER_SEC)

# ══════════════════════════════════════════════════════════════════════════════
#  STANDALONE TESTS
# ══════════════════════════════════════════════════════════════════════════════

def test_turn():
    print(f"TICKS_FOR_90 = {TICKS_FOR_90}")
    L0, R0 = _get_left(), _get_right()
    turn_right_90()
    print(f"  Left  ticks: {abs(_get_left()-L0)}  (target {TICKS_FOR_90})")
    print(f"  Right ticks: {abs(_get_right()-R0)}  (target {TICKS_FOR_90})")

def test_drive():
    drive_forward_cm(30.0)
    print(f"  Odometer: {get_total_distance_cm():.2f} cm")

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
        _stop_motors(0)
        pi.write(STBY, 0)
        pi.stop()
