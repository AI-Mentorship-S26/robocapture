"""
turn_verbose.py
───────────────
Runs the PID turn loop but prints every cycle so we can see
if ticks are counting and what the error is doing.
"""
import pigpio
import time
import math

# ── Config — must match pid_motion.py ─────────────────────────────────────────
AIN1, AIN2, PWMA = 6,  5,  12
BIN1, BIN2, PWMB = 16, 26, 13
STBY             = 25
LEFT_ENC_A,  LEFT_ENC_B  = 24, 25
RIGHT_ENC_A, RIGHT_ENC_B = 17, 27

SPEED       = 150
TICKS_FOR_90 = 2605   # ← paste YOUR measured value here

# ── pigpio ─────────────────────────────────────────────────────────────────────
pi = pigpio.pi()
if not pi.connected:
    print("ERROR: run 'sudo pigpiod' first"); exit()

for pin in [AIN1, AIN2, PWMA, BIN1, BIN2, PWMB, STBY]:
    pi.set_mode(pin, pigpio.OUTPUT)
pi.set_PWM_range(PWMA, 255);      pi.set_PWM_range(PWMB, 255)
pi.set_PWM_frequency(PWMA, 1000); pi.set_PWM_frequency(PWMB, 1000)
pi.write(STBY, 1)

# Encoders
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

# ── Turn ───────────────────────────────────────────────────────────────────────
L0, R0 = _L, _R

pi.write(AIN1, 1); pi.write(AIN2, 0)
pi.set_PWM_dutycycle(PWMA, SPEED)
pi.write(BIN1, 0); pi.write(BIN2, 1)
pi.set_PWM_dutycycle(PWMB, SPEED)

print(f"Turning... target={TICKS_FOR_90} ticks at PWM {SPEED}")
print(f"{'cycle':>6}  {'L':>6}  {'R':>6}  {'avg':>8}  {'error':>8}")

cycle = 0
try:
    while True:
        time.sleep(0.1)
        L = abs(_L - L0)
        R = abs(_R - R0)
        avg = (L + R) / 2.0
        err = TICKS_FOR_90 - avg
        cycle += 1
        print(f"{cycle:>6}  {L:>6}  {R:>6}  {avg:>8.1f}  {err:>8.1f}")

        if avg >= TICKS_FOR_90:
            print("TARGET REACHED — stopping")
            break

except KeyboardInterrupt:
    print("\nAborted by user")
finally:
    pi.set_PWM_dutycycle(PWMA, 0)
    pi.set_PWM_dutycycle(PWMB, 0)
    pi.write(AIN1, 0); pi.write(AIN2, 0)
    pi.write(BIN1, 0); pi.write(BIN2, 0)
    pi.write(STBY, 0)
    pi.stop()
