"""
test_turn_debug.py
──────────────────
Turns right at TEST_SPEED, prints live tick counts from both encoders.
Press Ctrl+C to stop at any time.
Run this to diagnose:
  1. Whether encoders are counting during a motor-driven turn
  2. How many ticks a 90° turn actually takes on your robot
"""
import pigpio
import time

# ── Pins ───────────────────────────────────────────────────────────────────────
AIN1, AIN2, PWMA = 6,  5,  12
BIN1, BIN2, PWMB = 16, 26, 13
STBY             = 25
LEFT_ENC_A,  LEFT_ENC_B  = 24, 25
RIGHT_ENC_A, RIGHT_ENC_B = 17, 27

TEST_SPEED = 150   # same speed as your calibration test

# ── pigpio ─────────────────────────────────────────────────────────────────────
pi = pigpio.pi()
if not pi.connected:
    print("ERROR: run 'sudo pigpiod' first")
    exit()

# Motor pins
for pin in [AIN1, AIN2, PWMA, BIN1, BIN2, PWMB, STBY]:
    pi.set_mode(pin, pigpio.OUTPUT)
pi.set_PWM_range(PWMA, 255);       pi.set_PWM_range(PWMB, 255)
pi.set_PWM_frequency(PWMA, 1000);  pi.set_PWM_frequency(PWMB, 1000)
pi.write(STBY, 1)

# Encoder state
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

# ── Right turn: left fwd, right rev ───────────────────────────────────────────
pi.write(AIN1, 1); pi.write(AIN2, 0)   # left forward
pi.set_PWM_dutycycle(PWMA, TEST_SPEED)
pi.write(BIN1, 0); pi.write(BIN2, 1)   # right reverse
pi.set_PWM_dutycycle(PWMB, TEST_SPEED)

print(f"Turning right at PWM {TEST_SPEED}...")
print("Watch the counts. Press Ctrl+C when the robot has turned EXACTLY 90°.")
print()

try:
    while True:
        L = abs(_L)
        R = abs(_R)
        avg = (L + R) / 2
        print(f"  L={L:5d}  R={R:5d}  avg={avg:6.1f}", end="\r")
        time.sleep(0.05)
except KeyboardInterrupt:
    pi.set_PWM_dutycycle(PWMA, 0)
    pi.set_PWM_dutycycle(PWMB, 0)
    pi.write(AIN1, 0); pi.write(AIN2, 0)
    pi.write(BIN1, 0); pi.write(BIN2, 0)
    pi.write(STBY, 0)
    L = abs(_L); R = abs(_R); avg = (L + R) / 2
    print(f"\n\n  Left ticks  : {L}")
    print(f"  Right ticks : {R}")
    print(f"  Average     : {avg:.1f}")
    print(f"\n  Paste into pid_motion.py:")
    print(f"      TICKS_FOR_90 = {int(round(avg))}")
    print(f"  (override the calculated value by adding this constant directly)")
    pi.stop()
