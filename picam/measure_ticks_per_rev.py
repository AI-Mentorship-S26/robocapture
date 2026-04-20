import pigpio
import time
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from encodersFull import Encoder

# ── Pins — match your robot ────────────────────────────────────────────────────
AIN1, AIN2, PWMA = 6,  5,  12
BIN1, BIN2, PWMB = 16, 26, 13
STBY             = 25
LEFT_ENC_A, LEFT_ENC_B = 24, 25

TEST_SPEED = 150   # match TURN_SPEED in pid_motion.py

pi = pigpio.pi()
for pin in [AIN1, AIN2, PWMA, BIN1, BIN2, PWMB, STBY]:
    pi.set_mode(pin, pigpio.OUTPUT)
pi.set_PWM_range(PWMA, 255)
pi.set_PWM_frequency(PWMA, 1000)
pi.write(STBY, 1)

enc = Encoder(pi, LEFT_ENC_A, LEFT_ENC_B, "left")
start = enc.getTick()

# spin left wheel only
pi.write(AIN1, 1); pi.write(AIN2, 0)
pi.set_PWM_dutycycle(PWMA, TEST_SPEED)

print("Spinning... press Ctrl+C after 5 full revolutions")
try:
    while True:
        print(f"  ticks: {abs(enc.getTick() - start)}", end="\r")
        time.sleep(0.05)
except KeyboardInterrupt:
    pi.set_PWM_dutycycle(PWMA, 0)
    pi.write(STBY, 0)
    total = abs(enc.getTick() - start)
    print(f"\n  Total ticks: {total}")
    print(f"  Ticks/rev  : {total / 5:.1f}  (divide by however many revs you did)")
    pi.stop()
