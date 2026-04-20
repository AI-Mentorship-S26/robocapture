import pigpio
import time

# ── Pins ───────────────────────────────────────────────────────────────────────
AIN1, AIN2, PWMA = 6,  5,  12
BIN1, BIN2, PWMB = 16, 26, 13
STBY             = 25
LEFT_ENC_A, LEFT_ENC_B = 24, 25

TEST_SPEED = 150

# ── Single pigpio instance — no import of encodersFull ────────────────────────
pi = pigpio.pi()
if not pi.connected:
    print("ERROR: pigpiod not running. Run: sudo pigpiod")
    exit()

# Motor pins
for pin in [AIN1, AIN2, PWMA, BIN1, BIN2, PWMB, STBY]:
    pi.set_mode(pin, pigpio.OUTPUT)
pi.set_PWM_range(PWMA, 255)
pi.set_PWM_frequency(PWMA, 1000)
pi.write(STBY, 1)

# Encoder pins
pi.set_mode(LEFT_ENC_A, pigpio.INPUT)
pi.set_mode(LEFT_ENC_B, pigpio.INPUT)
pi.set_pull_up_down(LEFT_ENC_A, pigpio.PUD_UP)
pi.set_pull_up_down(LEFT_ENC_B, pigpio.PUD_UP)
pi.set_glitch_filter(LEFT_ENC_A, 5)
pi.set_glitch_filter(LEFT_ENC_B, 5)

# Encoder state
tick_count = 0
prevA = pi.read(LEFT_ENC_A)
prevB = pi.read(LEFT_ENC_B)
lookup = [0,-1,1,0, 1,0,0,-1, -1,0,0,1, 0,1,-1,0]

def on_enc(gpio, level, _t):
    global tick_count, prevA, prevB
    if gpio == LEFT_ENC_A:
        currA, currB = level, pi.read(LEFT_ENC_B)
    else:
        currA, currB = pi.read(LEFT_ENC_A), level
    idx = (prevA << 3) | (prevB << 2) | (currA << 1) | currB
    tick_count += lookup[idx]
    prevA, prevB = currA, currB

pi.callback(LEFT_ENC_A, pigpio.EITHER_EDGE, on_enc)
pi.callback(LEFT_ENC_B, pigpio.EITHER_EDGE, on_enc)

# ── Spin ───────────────────────────────────────────────────────────────────────
pi.write(AIN1, 1)
pi.write(AIN2, 0)
pi.set_PWM_dutycycle(PWMA, TEST_SPEED)

print(f"Spinning left wheel at PWM {TEST_SPEED}...")
print("Press Ctrl+C after exactly 5 full revolutions")

try:
    while True:
        print(f"  ticks: {abs(tick_count)}", end="\r")
        time.sleep(0.05)
except KeyboardInterrupt:
    pi.set_PWM_dutycycle(PWMA, 0)
    pi.write(AIN1, 0)
    pi.write(STBY, 0)
    total = abs(tick_count)
    print(f"\n  Total ticks : {total}")
    print(f"  Ticks/rev   : {total / 5:.1f}")
    print(f"\n  Paste into pid_motion.py:  TICKS_PER_REV = {int(round(total / 5))}")
    pi.stop()
