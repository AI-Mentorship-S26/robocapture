"""
pid_motion.py
─────────────
Encoder-based PID motion controller for your differential-drive robot.

DROP-IN REPLACEMENT for the timed turn/drive helpers in robot_rl_nav.py.
Import this module and call the functions below instead of the originals.

QUICK-START
  1. Wire your encoders as in encodersFull.py (already done).
  2. Run this file directly once to calibrate:
         python3 pid_motion.py --calibrate
     Follow the prompts — it sets TICKS_PER_REV and WHEEL_DIAMETER_CM for you.
  3. In robot_rl_nav.py, replace:
         from robot_rl_nav import turn_right_90, turn_left_90, drive_forward
     with:
         from pid_motion import turn_right_90, turn_left_90, drive_forward_cm

TUNING PID GAINS  (if turns overshoot or oscillate)
  Start with Kp only (Ki=0, Kd=0).  Increase Kp until it just starts to
  oscillate, then back off ~30%.  Add Kd to damp oscillation.
  Ki is usually small (0.001–0.01) — only needed if there's steady-state error.

  Separate gain sets are used for turning (TURN_*) and driving (DRIVE_*).
"""

import time
import argparse
import pigpio

# ── Encoder import ─────────────────────────────────────────────────────────────
# Re-uses your existing Encoder class unchanged.
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from encodersFull import Encoder   # your quadrature encoder class

# ══════════════════════════════════════════════════════════════════════════════
#  CONFIGURATION  — edit these after calibration
# ══════════════════════════════════════════════════════════════════════════════

# ── Robot geometry ─────────────────────────────────────────────────────────────
TICKS_PER_REV      = 620      # encoder ticks for one full wheel revolution
                               # (set by --calibrate, or measure manually)
WHEEL_DIAMETER_CM  = 6.5      # wheel outer diameter in centimetres
WHEELBASE_CM       = 17.0     # centre-to-centre distance between wheels (cm)
                               # used to convert turn angle → wheel arc length

# ── Motor pins  (must match robot_rl_nav.py) ──────────────────────────────────
AIN1, AIN2, PWMA = 6,  5,  12   # left  motor
BIN1, BIN2, PWMB = 16, 26, 13   # right motor
STBY             = 25

# ── Encoder pins (must match encodersFull.py) ─────────────────────────────────
LEFT_ENC_A,  LEFT_ENC_B  = 24, 25
RIGHT_ENC_A, RIGHT_ENC_B = 17, 27

# ── PID gains — TURNING ────────────────────────────────────────────────────────
# Error signal = target_tick_delta − actual_tick_delta
# (tick_delta = rightTicks − leftTicks for a right turn; negated for left)
TURN_KP = 2.5     # proportional — main corrective force
TURN_KI = 0.004   # integral     — eliminates steady-state error
TURN_KD = 0.8     # derivative   — damps oscillation / overshoot

TURN_BASE_SPEED    = 120   # PWM starting speed (0-255) while turning
TURN_MIN_SPEED     = 60    # minimum PWM so motors don't stall
TURN_MAX_SPEED     = 200   # maximum PWM cap
TURN_SETTLE_TICKS  = 3     # stop when error ≤ this many ticks for N cycles
TURN_SETTLE_CYCLES = 5     # number of consecutive cycles within tolerance

# ── PID gains — DRIVING STRAIGHT ──────────────────────────────────────────────
# Error signal = leftTicks − rightTicks  (should stay near 0 while driving)
DRIVE_KP = 1.8
DRIVE_KI = 0.002
DRIVE_KD = 0.5

DRIVE_BASE_SPEED = 180   # forward PWM
DRIVE_MIN_SPEED  = 80
DRIVE_MAX_SPEED  = 230

# ── Timing ─────────────────────────────────────────────────────────────────────
PID_LOOP_HZ  = 50          # control loop rate (Hz)
PID_DT       = 1.0 / PID_LOOP_HZ

STABILISE_SEC = 0.3        # coast-and-settle pause after each move

# ══════════════════════════════════════════════════════════════════════════════
#  DERIVED CONSTANTS  (computed from geometry — don't touch)
# ══════════════════════════════════════════════════════════════════════════════

import math

WHEEL_CIRC_CM       = math.pi * WHEEL_DIAMETER_CM          # cm per revolution
TICKS_PER_CM        = TICKS_PER_REV / WHEEL_CIRC_CM        # ticks per cm of travel

# For a point turn (one wheel fwd, one rev) the arc each wheel traces is:
#   arc = (angle_deg / 360) × π × wheelbase
# TICKS_FOR_90 is how many ticks each wheel must move for a 90° point turn.
TICKS_FOR_90 = int((90.0 / 360.0) * math.pi * WHEELBASE_CM * TICKS_PER_CM)


# ══════════════════════════════════════════════════════════════════════════════
#  HARDWARE INIT
# ══════════════════════════════════════════════════════════════════════════════

pi = pigpio.pi()
if not pi.connected:
    raise RuntimeError("Cannot connect to pigpiod — run 'sudo pigpiod' first.")

for pin in [AIN1, AIN2, PWMA, BIN1, BIN2, PWMB, STBY]:
    pi.set_mode(pin, pigpio.OUTPUT)

pi.set_PWM_range(PWMA, 255);        pi.set_PWM_range(PWMB, 255)
pi.set_PWM_frequency(PWMA, 1000);   pi.set_PWM_frequency(PWMB, 1000)
pi.write(STBY, 1)

leftEnc  = Encoder(pi, LEFT_ENC_A,  LEFT_ENC_B,  "left")
rightEnc = Encoder(pi, RIGHT_ENC_A, RIGHT_ENC_B, "right")


# ══════════════════════════════════════════════════════════════════════════════
#  LOW-LEVEL MOTOR HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _set_motors(left_pwm: int, right_pwm: int):
    """Set motor speeds.  Positive = forward, negative = reverse."""
    left_pwm  = max(-255, min(255, left_pwm))
    right_pwm = max(-255, min(255, right_pwm))

    # Left motor (A)
    if left_pwm >= 0:
        pi.write(AIN1, 1); pi.write(AIN2, 0)
        pi.set_PWM_dutycycle(PWMA, left_pwm)
    else:
        pi.write(AIN1, 0); pi.write(AIN2, 1)
        pi.set_PWM_dutycycle(PWMA, abs(left_pwm))

    # Right motor (B)
    if right_pwm >= 0:
        pi.write(BIN1, 1); pi.write(BIN2, 0)
        pi.set_PWM_dutycycle(PWMB, right_pwm)
    else:
        pi.write(BIN1, 0); pi.write(BIN2, 1)
        pi.set_PWM_dutycycle(PWMB, abs(right_pwm))


def _stop_motors(coast_sec: float = STABILISE_SEC):
    _set_motors(0, 0)
    time.sleep(coast_sec)


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


# ══════════════════════════════════════════════════════════════════════════════
#  PID STATE HELPER
# ══════════════════════════════════════════════════════════════════════════════

class _PID:
    """Minimal PID accumulator — one instance per motion segment."""
    def __init__(self, kp: float, ki: float, kd: float):
        self.kp, self.ki, self.kd = kp, ki, kd
        self.integral   = 0.0
        self.prev_error = 0.0

    def compute(self, error: float, dt: float) -> float:
        self.integral  += error * dt
        derivative      = (error - self.prev_error) / dt if dt > 0 else 0.0
        self.prev_error = error
        return self.kp * error + self.ki * self.integral + self.kd * derivative


# ══════════════════════════════════════════════════════════════════════════════
#  TURN  (encoder-closed-loop PID)
# ══════════════════════════════════════════════════════════════════════════════

def _turn(direction: int, target_ticks: int = TICKS_FOR_90):
    """
    Execute a PID-controlled point turn.

    Parameters
    ----------
    direction    :  +1 = turn right,  -1 = turn left
    target_ticks :  encoder ticks each wheel should travel (default = 90°)

    For a RIGHT turn:  left wheel goes FORWARD, right wheel goes BACKWARD.
    For a LEFT  turn:  right wheel goes FORWARD, left wheel goes BACKWARD.

    The PID error is:
        error = target_ticks − ticks_traveled_so_far

    Both encoders are monitored independently and their average tick-travel
    is used as the process variable, with per-wheel speed trim applied if
    they diverge (handles motor asymmetry).
    """
    # Snapshot encoder positions at start
    L0 = leftEnc.getTick()
    R0 = rightEnc.getTick()

    pid          = _PID(TURN_KP, TURN_KI, TURN_KD)
    settle_count = 0
    last_time    = time.monotonic()

    print(f"  [PID Turn] dir={'+' if direction>0 else '-'} target={target_ticks} ticks")

    while True:
        now  = time.monotonic()
        dt   = now - last_time
        if dt < PID_DT:
            time.sleep(PID_DT - dt)
            continue
        last_time = now

        # How far has each wheel moved (unsigned)?
        L_moved = abs(leftEnc.getTick()  - L0)
        R_moved = abs(rightEnc.getTick() - R0)
        avg_moved = (L_moved + R_moved) / 2.0

        error = target_ticks - avg_moved

        # Settle check
        if abs(error) <= TURN_SETTLE_TICKS:
            settle_count += 1
            if settle_count >= TURN_SETTLE_CYCLES:
                print(f"  [PID Turn] done  L={L_moved}  R={R_moved}  err={error:.1f}")
                break
        else:
            settle_count = 0

        # PID output → base speed
        output = pid.compute(error, dt)
        base   = _clamp(abs(output), TURN_MIN_SPEED, TURN_MAX_SPEED)

        # Wheel-balance trim: if one wheel is ahead, slow it slightly
        imbalance  = (L_moved - R_moved) * 0.3   # small correction factor
        left_pwm   = base - imbalance
        right_pwm  = base + imbalance
        left_pwm   = _clamp(left_pwm,  TURN_MIN_SPEED, TURN_MAX_SPEED)
        right_pwm  = _clamp(right_pwm, TURN_MIN_SPEED, TURN_MAX_SPEED)

        # Apply direction:  right turn → left fwd, right rev  (and vice-versa)
        _set_motors(
            int(direction  * left_pwm),    # left  wheel
            int(-direction * right_pwm)    # right wheel
        )

    _stop_motors()


# Public API — match robot_rl_nav.py names exactly
def turn_right_90():
    """PID-controlled 90° right turn.  Replaces the timed version."""
    _turn(direction=+1)


def turn_left_90():
    """PID-controlled 90° left turn.  Replaces the timed version."""
    _turn(direction=-1)


# ══════════════════════════════════════════════════════════════════════════════
#  DRIVE FORWARD  (encoder-closed-loop PID, distance-based)
# ══════════════════════════════════════════════════════════════════════════════

# Running odometry — cumulative distance driven this session (cm)
_total_distance_cm = 0.0

def get_total_distance_cm() -> float:
    """Return total distance driven since module load (or last reset)."""
    return _total_distance_cm

def reset_distance():
    """Reset the odometry counter."""
    global _total_distance_cm
    _total_distance_cm = 0.0


def drive_forward_cm(distance_cm: float):
    """
    Drive forward a precise distance (in centimetres) using PID.

    The straight-line PID corrects steering by comparing left vs right ticks.
    If the left wheel is ahead of the right, we slow the left motor slightly
    (and vice-versa) to keep the robot tracking straight.

    Parameters
    ----------
    distance_cm : how far to travel (centimetres)

    Updates the global odometry counter automatically.
    """
    global _total_distance_cm

    target_ticks = distance_cm * TICKS_PER_CM

    L0 = leftEnc.getTick()
    R0 = rightEnc.getTick()

    pid          = _PID(DRIVE_KP, DRIVE_KI, DRIVE_KD)
    last_time    = time.monotonic()

    print(f"  [PID Drive] target={distance_cm:.1f}cm  ({target_ticks:.0f} ticks)")

    while True:
        now = time.monotonic()
        dt  = now - last_time
        if dt < PID_DT:
            time.sleep(PID_DT - dt)
            continue
        last_time = now

        L_moved = leftEnc.getTick()  - L0
        R_moved = rightEnc.getTick() - R0
        avg_moved = (L_moved + R_moved) / 2.0

        # Distance remaining
        remaining = target_ticks - avg_moved
        if remaining <= 0:
            break

        # Steering correction: left-right tick imbalance
        steer_error = L_moved - R_moved
        steer_corr  = pid.compute(steer_error, dt)

        # Speed profile: ramp down in last 20% of distance to prevent overshoot
        progress = avg_moved / target_ticks if target_ticks > 0 else 1.0
        if progress > 0.8:
            # Linear ramp from DRIVE_BASE_SPEED → DRIVE_MIN_SPEED
            ramp_factor = 1.0 - ((progress - 0.8) / 0.2)
            speed = DRIVE_MIN_SPEED + ramp_factor * (DRIVE_BASE_SPEED - DRIVE_MIN_SPEED)
        else:
            speed = DRIVE_BASE_SPEED

        left_pwm  = _clamp(speed - steer_corr, DRIVE_MIN_SPEED, DRIVE_MAX_SPEED)
        right_pwm = _clamp(speed + steer_corr, DRIVE_MIN_SPEED, DRIVE_MAX_SPEED)
        _set_motors(int(left_pwm), int(right_pwm))

    _stop_motors()

    # Update odometry
    L_final = abs(leftEnc.getTick()  - L0)
    R_final = abs(rightEnc.getTick() - R0)
    actual_ticks = (L_final + R_final) / 2.0
    actual_cm    = actual_ticks / TICKS_PER_CM
    _total_distance_cm += actual_cm
    print(f"  [PID Drive] done  actual={actual_cm:.2f}cm  total={_total_distance_cm:.2f}cm")


def drive_forward(duration_sec: float = 1.5):
    """
    Compatibility shim for robot_rl_nav.py which passes a duration in seconds.
    Converts duration × estimated speed into a cm target.

    For best accuracy, replace calls in robot_rl_nav.py with drive_forward_cm()
    and pass explicit distances.  This shim lets you do a zero-change drop-in.
    """
    # Rough cm estimate: base speed / 255 × ~30 cm/s (tune to your robot)
    ESTIMATED_CM_PER_SEC = 25.0
    estimated_cm = duration_sec * ESTIMATED_CM_PER_SEC
    drive_forward_cm(estimated_cm)


# ══════════════════════════════════════════════════════════════════════════════
#  CALIBRATION ROUTINE
# ══════════════════════════════════════════════════════════════════════════════

def calibrate():
    """
    Interactive calibration.  Run once with:
        python3 pid_motion.py --calibrate

    Steps:
      1. Ticks-per-revolution: spin one wheel exactly one turn by hand,
         read the encoder count.
      2. 90° turn ticks: robot executes a timed turn, you measure the actual
         angle and we compute a correction factor.
      3. Prints the constants to paste into this file.
    """
    print("\n══════ ENCODER CALIBRATION ══════")
    print("Step 1: Ticks per revolution")
    print("  Lift one wheel off the ground.")
    print("  Press ENTER, rotate the LEFT wheel exactly ONE full turn by hand,")
    print("  then press ENTER again.")
    input("  [ENTER to start counting] ")
    L0 = leftEnc.getTick()
    input("  Rotate the wheel one full revolution now, then press [ENTER] ")
    ticks = abs(leftEnc.getTick() - L0)
    print(f"  → Measured ticks/rev = {ticks}")

    print("\nStep 2: Wheel diameter")
    print("  Place the robot on a flat surface.")
    print("  Mark the contact point of the LEFT wheel on the floor.")
    print("  Drive forward exactly ONE wheel revolution (manually push or use timed drive).")
    raw_diam = input("  Measure the distance travelled in cm, enter it here: ")
    try:
        circ_cm  = float(raw_diam)
        diam_cm  = circ_cm / math.pi
    except ValueError:
        print("  Invalid input, using default 6.5 cm diameter.")
        diam_cm = 6.5

    ticks_per_cm = ticks / (math.pi * diam_cm)

    print("\nStep 3: Wheelbase")
    raw_wb = input("  Measure wheel centre-to-centre distance in cm: ")
    try:
        wheelbase = float(raw_wb)
    except ValueError:
        print("  Invalid input, using default 17.0 cm.")
        wheelbase = 17.0

    ticks_for_90 = int((90.0 / 360.0) * math.pi * wheelbase * ticks_per_cm)

    print("\n══════ CALIBRATION RESULTS ══════")
    print(f"  TICKS_PER_REV     = {ticks}")
    print(f"  WHEEL_DIAMETER_CM = {diam_cm:.2f}")
    print(f"  WHEELBASE_CM      = {wheelbase:.2f}")
    print(f"  → TICKS_PER_CM    = {ticks_per_cm:.2f}")
    print(f"  → TICKS_FOR_90    = {ticks_for_90}")
    print("\nPaste these values into pid_motion.py at the top of the file.")
    print("Then run a 90° turn test:  python3 pid_motion.py --test-turn")


def test_turn():
    """Quick test: execute one 90° right turn and print encoder counts."""
    print("Executing one 90° right turn (PID)…")
    L0, R0 = leftEnc.getTick(), rightEnc.getTick()
    turn_right_90()
    L1, R1 = leftEnc.getTick(), rightEnc.getTick()
    print(f"  Left  ticks: {abs(L1-L0)}  (target {TICKS_FOR_90})")
    print(f"  Right ticks: {abs(R1-R0)}  (target {TICKS_FOR_90})")
    print(f"  Imbalance  : {abs(abs(L1-L0) - abs(R1-R0))} ticks")


def test_drive():
    """Quick test: drive forward 30 cm and print actual distance."""
    print("Driving forward 30 cm (PID)…")
    drive_forward_cm(30.0)
    print(f"  Odometer: {get_total_distance_cm():.2f} cm")


# ══════════════════════════════════════════════════════════════════════════════
#  STANDALONE ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PID motion controller tests")
    parser.add_argument("--calibrate",  action="store_true", help="Run calibration wizard")
    parser.add_argument("--test-turn",  action="store_true", help="Test one 90° right turn")
    parser.add_argument("--test-drive", action="store_true", help="Test 30 cm forward drive")
    args = parser.parse_args()

    try:
        if args.calibrate:
            calibrate()
        elif args.test_turn:
            test_turn()
        elif args.test_drive:
            test_drive()
        else:
            parser.print_help()
    finally:
        _stop_motors(0)
        pi.write(STBY, 0)
        pi.stop()
