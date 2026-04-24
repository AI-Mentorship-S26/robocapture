"""
ultrasonic.py — standalone HC-SR04 test
Run on the Pi:  python3 picam/ultrasonic.py

Wiring (3.3V — no voltage divider needed):
  VCC  → Pin 1  (3.3V)
  GND  → Pin 6  (GND)
  TRIG → Pin 16 (GPIO 23)
  ECHO → Pin 15 (GPIO 22)
"""

import time
import pigpio

TRIG             = 23
ECHO             = 22
STOP_DISTANCE_CM = 25

pi = pigpio.pi()
if not pi.connected:
    raise RuntimeError("Cannot connect to pigpiod — run 'sudo pigpiod' first.")

pi.set_mode(TRIG, pigpio.OUTPUT)
pi.set_mode(ECHO, pigpio.INPUT)
pi.write(TRIG, 0)
time.sleep(0.5)   # let sensor settle on startup

def get_distance() -> float:
    """Return distance in cm, or 999.0 on timeout."""
    pi.write(TRIG, 0)
    time.sleep(0.00005)
    pi.write(TRIG, 1)
    time.sleep(0.00001)
    pi.write(TRIG, 0)

    timeout = time.time() + 0.1
    while pi.read(ECHO) == 0:
        if time.time() > timeout:
            return 999.0
    pulse_start = time.time()

    timeout = time.time() + 0.1
    while pi.read(ECHO) == 1:
        if time.time() > timeout:
            return 999.0
    pulse_end = time.time()

    return round((pulse_end - pulse_start) * 17150, 2)


if __name__ == "__main__":
    print(f"HC-SR04 test — obstacle threshold: {STOP_DISTANCE_CM} cm")
    print("Point sensor at objects and move your hand closer/further.")
    print("Press Ctrl+C to stop.\n")
    try:
        while True:
            dist = get_distance()
            if dist == 999.0:
                print("  [TIMEOUT] No echo received — check wiring", flush=True)
            elif dist < STOP_DISTANCE_CM:
                print(f"  !! OBSTACLE at {dist:.1f} cm (within {STOP_DISTANCE_CM} cm threshold)", flush=True)
            else:
                print(f"  Distance: {dist:.1f} cm — clear", flush=True)
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        pi.stop()
