"""
measure_ticks_per_rev.py
────────────────────────
Spins one wheel at navigation speed for a set number of rotations,
then reports ticks/rev.

Run from your robot code directory:
    python3 measure_ticks_per_rev.py

Make sure pigpiod is running first:
    sudo pigpiod
"""

import pigpio
import time
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from encodersFull import Encoder

# ── Config — match these to pid_motion.py ─────────────────────────────────────

# Motor pins
AIN1, AIN2, PWMA = 6,  5,  12   # left motor
BIN1, BIN2, PWMB = 16, 26, 13   # right motor
STBY             = 25

# Encoder pins
LEFT_ENC_A,  LEFT_ENC_B  = 24, 25
RIGHT_ENC_A, RIGHT_ENC_B = 17, 27

# Speed to test at — set this to whatever TURN_SPEED is in pid_motion.py
TEST_SPEED = 150   # PWM 0-255

# How many full revolutions to spin (more = more accurate average)
NUM_REVOLUTIONS = 5

# Safety timeout — if the wheel hasn't hit the target in this many seconds, abort
TIMEOUT_SEC = 15

# Rough ticks/rev estimate just for the timeout/target logic.
# This doesn't need to be accurate — it's only used to know when to stop.
# If you have no idea, 300-1000 is a safe range for most hobby encoders.
ROUGH_TICKS_PER_REV = 500

# ── Hardware init ──────────────────────────────────────────────────────────────

pi = pigpio.pi()
if not pi.connected:
    print("ERROR: Cannot connect to pigpiod. Run 'sudo pigpiod' first.")
    sys.exit(1)

for pin in [AIN1, AIN2, PWMA, BIN1, BIN2, PWMB, STBY]:
    pi.set_mode(pin, pigpio.OUTPUT)

pi.set_PWM_range(PWMA, 255);        pi.set_PWM_range(PWMB, 255)
pi.set_PWM_frequency(PWMA, 1000);   pi.set_PWM_frequency(PWMB, 1000)
pi.write(STBY, 1)

leftEnc  = Encoder(pi, LEFT_ENC_A,  LEFT_ENC_B,  "left")
rightEnc = Encoder(pi, RIGHT_ENC_A, RIGHT_ENC_B, "right")

# ── Motor helpers ──────────────────────────────────────────────────────────────

def spin_left_forward(speed):
    pi.write(AIN1, 1); pi.write(AIN2, 0)
    pi.set_PWM_dutycycle(PWMA, speed)
    pi.write(BIN1, 0); pi.write(BIN2, 0)   # right wheel stopped
    pi.set_PWM_dutycycle(PWMB, 0)

def stop_all():
    pi.set_PWM_dutycycle(PWMA, 0)
    pi.set_PWM_dutycycle(PWMB, 0)
    pi.write(AIN1, 0); pi.write(AIN2, 0)
    pi.write(BIN1, 0); pi.write(BIN2, 0)

# ── Measurement ───────────────────────────────────────────────────────────────

def measure(wheel: str = "left") -> float:
    """
    Spin the chosen wheel at TEST_SPEED for NUM_REVOLUTIONS,
    return the average ticks per revolution.
    """
    target_ticks = ROUGH_TICKS_PER_REV * NUM_REVOLUTIONS

    print(f"\n── Measuring {wheel} wheel ──────────────────────────")
    print(f"   Speed    : {TEST_SPEED} PWM")
    print(f"   Revs     : {NUM_REVOLUTIONS}")
    print(f"   Target   : ~{target_ticks} ticks (rough estimate)")
    print(f"   Timeout  : {TIMEOUT_SEC}s")
    print()
    input("   Lift the robot so the wheel spins freely, then press ENTER...")

    enc   = leftEnc if wheel == "left" else rightEnc
    start = enc.getTick()

    print(f"   Spinning {wheel} wheel at PWM {TEST_SPEED}...")
    spin_left_forward(TEST_SPEED)

    deadline = time.monotonic() + TIMEOUT_SEC
    while True:
        elapsed = time.monotonic()
        ticks   = abs(enc.getTick() - start)
        print(f"   ticks so far: {ticks:5d}  (target ~{target_ticks})", end="\r")

        if ticks >= target_ticks:
            stop_all()
            final_ticks = abs(enc.getTick() - start)
            print(f"\n   Stopped.  Total ticks: {final_ticks}")
            avg = final_ticks / NUM_REVOLUTIONS
            print(f"   Ticks/rev  : {avg:.1f}")
            return avg

        if elapsed > deadline:
            stop_all()
            ticks_now = abs(enc.getTick() - start)
            print(f"\n   TIMEOUT after {TIMEOUT_SEC}s — only got {ticks_now} ticks.")
            print("   Either ROUGH_TICKS_PER_REV is way off, or the encoder isn't wired correctly.")
            return None

        time.sleep(0.02)

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("═" * 55)
    print("  Ticks-per-revolution calibration")
    print("  Motor speed:", TEST_SPEED, "PWM  |  Revolutions:", NUM_REVOLUTIONS)
    print("═" * 55)

    try:
        # Measure left wheel
        left_tpr = measure("left")

        time.sleep(0.5)

        # Measure right wheel (swap spin function below if needed)
        print("\n── Measuring RIGHT wheel ───────────────────────────")
        print("   (same process, right wheel only)")
        input("   Press ENTER when ready...")

        enc   = rightEnc
        start = enc.getTick()

        # Spin right wheel only
        pi.write(BIN1, 1); pi.write(BIN2, 0)
        pi.set_PWM_dutycycle(PWMB, TEST_SPEED)
        pi.write(AIN1, 0); pi.write(AIN2, 0)
        pi.set_PWM_dutycycle(PWMA, 0)

        target_ticks = ROUGH_TICKS_PER_REV * NUM_REVOLUTIONS
        deadline     = time.monotonic() + TIMEOUT_SEC

        while True:
            ticks = abs(enc.getTick() - start)
            print(f"   ticks so far: {ticks:5d}  (target ~{target_ticks})", end="\r")
            if ticks >= target_ticks:
                stop_all()
                final_ticks = abs(enc.getTick() - start)
                right_tpr = final_ticks / NUM_REVOLUTIONS
                print(f"\n   Stopped.  Total ticks: {final_ticks}")
                print(f"   Ticks/rev  : {right_tpr:.1f}")
                break
            if time.monotonic() > deadline:
                stop_all()
                print(f"\n   TIMEOUT — only got {abs(enc.getTick()-start)} ticks.")
                right_tpr = None
                break
            time.sleep(0.02)

    except KeyboardInterrupt:
        stop_all()
        print("\n\nAborted.")
        return

    finally:
        stop_all()
        pi.write(STBY, 0)
        pi.stop()

    # ── Results ───────────────────────────────────────────────────────────────
    print()
    print("═" * 55)
    print("  RESULTS")
    print("═" * 55)
    if left_tpr:
        print(f"  Left  wheel ticks/rev : {left_tpr:.1f}")
    if right_tpr:
        print(f"  Right wheel ticks/rev : {right_tpr:.1f}")

    if left_tpr and right_tpr:
        avg_tpr = (left_tpr + right_tpr) / 2
        diff    = abs(left_tpr - right_tpr)
        print(f"  Average               : {avg_tpr:.1f}")
        print(f"  Wheel imbalance       : {diff:.1f} ticks  ", end="")
        if diff < 10:
            print("(excellent ✓)")
        elif diff < 30:
            print("(acceptable — PID will correct)")
        else:
            print("(large — check encoder wiring or motor condition)")

        print()
        print("  Paste this into pid_motion.py:")
        print(f"      TICKS_PER_REV = {int(round(avg_tpr))}")
    print("═" * 55)

if __name__ == "__main__":
    main()
