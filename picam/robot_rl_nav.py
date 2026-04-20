"""
robot_rl_nav.py
───────────────
360-survey → RL inference → navigate loop.

HOW IT WORKS
  1. Stop and stabilise.
  2. Take a photo, turn 90° right, repeat ×4  →  images[0..3]
       dir 0 = forward (original heading)
       dir 1 = 90° right
       dir 2 = 180° (behind)
       dir 3 = 90° left
  3. Pass all four images to your RL model.
  4. Pick the best direction from the returned scores.
  5. Turn to face that direction, drive forward, repeat.

RL MODEL INTERFACE
  All models return 0 (skip) or 1 (good) per direction.
  The active model is controlled by set_current_model(), which pi_server.py
  calls whenever the frontend sends a setModel: message — keeping this file
  and the WebSocket server in sync with no extra IPC needed.

  If multiple directions score 1 the robot prefers direction 0 (forward).
  If no direction scores 1 the robot stays and re-surveys.

CAMERA
  Delegates to your existing run_capture() / capture_once.py pipeline.
  capture_once.py saves each JPEG under captures/ and prints the path.
  survey_360() returns a list of 4 file paths (strings), one per direction.
  query_rl_model() receives those paths — open them however your model needs.

WIRING  (unchanged from your original)
  AIN1=6  AIN2=5   PWMA=12
  BIN1=16 BIN2=26  PWMB=13
  STBY=25

MOTION
  Turns and forward drive are handled by pid_motion.py (encoder-closed-loop PID).
  turn_right_90(), turn_left_90(), drive_forward(), drive_forward_cm() are all
  imported from there — no timed guesswork.
"""

import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
import pigpio

# Allow imports from the same directory as this file (where rl_models.py lives)
sys.path.insert(0, str(Path(__file__).parent))

from image_preprocessing import ImagePreprocessingPipeline
from rl_models import (
    run_random,            update_random,            nav_score_random,
    run_contextual_bandit, update_contextual_bandit,  nav_score_contextual_bandit,
    run_deep_contextual_bandit, update_deep_contextual_bandit,  nav_score_deep_contextual_bandit,
    run_sarsa,             update_sarsa,              nav_score_sarsa,
    run_dqn,               update_dqn,               nav_score_dqn,
    run_ppo,               update_ppo,               nav_score_ppo,
    run_reinforce,         update_reinforce,          nav_score_reinforce,
    run_aac,               update_aac,               nav_score_aac,
    run_tiny_sac,          update_tiny_sac,           nav_score_tiny_sac,
)

# ── PID motion controller (encoder-closed-loop) ────────────────────────────────
# Replaces the old timed turn_right_90 / turn_left_90 / drive_forward helpers.
from pid_motion import (
    turn_right_90,          # PID-controlled 90° right turn
    turn_left_90,           # PID-controlled 90° left turn
    drive_forward,          # duration-based shim → converts seconds → cm internally
    drive_forward_cm,       # use this when you want an exact distance in cm
    get_total_distance_cm,  # cumulative odometry for this session
    reset_distance,         # reset odometry counter to zero
)

is_navigating = False

# ── WebSocket image callback ───────────────────────────────────────────────────
send_image_callback = None
def set_send_callback(callback):
    global send_image_callback
    send_image_callback = callback

# ── Configuration ──────────────────────────────────────────────────────────────

DRIVE_SPEED   = 200        # PWM 0-255 — still used by set_motors() / stop()
DRIVE_FWD_SEC = 1.5        # seconds passed to drive_forward() shim each cycle
STABILISE_SEC = 0.8        # pause after stopping before taking a photo

# ── Pin definitions ────────────────────────────────────────────────────────────

AIN1, AIN2, PWMA = 6,  5,  12
BIN1, BIN2, PWMB = 16, 26, 13
STBY             = 25

# ── RL model registry + shared state ──────────────────────────────────────────

MODEL_MAP = {
    "random":                 (run_random,                 update_random),
    "contextual_bandit":      (run_contextual_bandit,       update_contextual_bandit),
    "deep_contextual_bandit": (run_deep_contextual_bandit,  update_deep_contextual_bandit),
    "sarsa":                  (run_sarsa,                   update_sarsa),
    "dqn":                    (run_dqn,                    update_dqn),
    "ppo":                    (run_ppo,                    update_ppo),
    "reinforce":              (run_reinforce,               update_reinforce),
    "aac":                    (run_aac,                    update_aac),
    "tiny_sac":               (run_tiny_sac,               update_tiny_sac),
}

NAV_SCORE_MAP = {
    "random":                 nav_score_random,
    "contextual_bandit":      nav_score_contextual_bandit,
    "deep_contextual_bandit": nav_score_deep_contextual_bandit,
    "sarsa":                  nav_score_sarsa,
    "dqn":                    nav_score_dqn,
    "ppo":                    nav_score_ppo,
    "reinforce":              nav_score_reinforce,
    "aac":                    nav_score_aac,
    "tiny_sac":               nav_score_tiny_sac,
}

current_model = "deep_contextual_bandit"
pipeline      = ImagePreprocessingPipeline()

def set_current_model(model_name: str):
    """
    Call this from pi_server.py when a setModel: message arrives:

        elif message.startswith("setModel:"):
            current_model = message.split(":")[1]
            robot_rl_nav.set_current_model(current_model)
    """
    global current_model
    if model_name not in MODEL_MAP:
        print(f"  [WARN] Unknown model '{model_name}' — keeping '{current_model}'")
        return
    current_model = model_name
    print(f"  [Nav] Active model switched to: {current_model}")

# ── pigpio init ────────────────────────────────────────────────────────────────

pi = pigpio.pi()
if not pi.connected:
    raise RuntimeError(
        "Cannot connect to pigpiod — run 'sudo pigpiod' first."
    )

for pin in [AIN1, AIN2, PWMA, BIN1, BIN2, PWMB, STBY]:
    pi.set_mode(pin, pigpio.OUTPUT)

pi.set_PWM_range(PWMA, 255);      pi.set_PWM_range(PWMB, 255)
pi.set_PWM_frequency(PWMA, 1000); pi.set_PWM_frequency(PWMB, 1000)
pi.write(STBY, 1)

# ── Camera: path to your existing capture script ──────────────────────────────

_SCRIPT_DIR     = os.path.dirname(os.path.abspath(__file__))
_CAPTURE_SCRIPT = os.path.join(_SCRIPT_DIR, "capture_once.py")

# ── Low-level motor control ────────────────────────────────────────────────────
# Kept for stop() — pid_motion.py has its own independent motor calls.

def set_motors(left_speed: int, right_speed: int):
    left_speed  = max(-255, min(255, left_speed))
    right_speed = max(-255, min(255, right_speed))

    if left_speed >= 0:
        pi.write(AIN1, 1); pi.write(AIN2, 0)
        pi.set_PWM_dutycycle(PWMA, left_speed)
    else:
        pi.write(AIN1, 0); pi.write(AIN2, 1)
        pi.set_PWM_dutycycle(PWMA, abs(left_speed))

    if right_speed >= 0:
        pi.write(BIN1, 1); pi.write(BIN2, 0)
        pi.set_PWM_dutycycle(PWMB, right_speed)
    else:
        pi.write(BIN1, 0); pi.write(BIN2, 1)
        pi.set_PWM_dutycycle(PWMB, abs(right_speed))

def run_command(left: int, right: int, duration: float, label: str = ""):
    if label:
        print(f"  [{label}] L={left} R={right} for {duration:.2f}s")
    set_motors(left, right)
    time.sleep(duration)
    set_motors(0, 0)
    time.sleep(0.05)

def stop(duration: float = STABILISE_SEC):
    run_command(0, 0, duration, "Stop")

# ── Camera capture ─────────────────────────────────────────────────────────────

def run_capture() -> str:
    """
    Mirrors run_capture() in pi_server.py exactly.
    Calls capture_once.py in a subprocess; returns the saved JPEG path.
    """
    proc = subprocess.run(
        ["python3", _CAPTURE_SCRIPT],
        capture_output=True, text=True
    )
    image_path = proc.stdout.strip()
    if proc.returncode == 0 and image_path and os.path.exists(image_path):
        return image_path
    raise RuntimeError(
        f"capture_once.py failed (rc={proc.returncode}): {proc.stderr.strip()}"
    )

# ── 360° survey ───────────────────────────────────────────────────────────────

def survey_360() -> list[str]:
    """
    Capture images in 4 directions (0°, 90°, 180°, 270°) by turning right.
    Turns are PID-controlled via pid_motion.turn_right_90().

    Returns
    -------
    image_paths : list of 4 file path strings
        [0] → current heading (forward)
        [1] → 90° right
        [2] → 180° (behind)
        [3] → 270° (left / 90° left of forward)

    After this function returns the robot is facing 270° from its original
    heading.  face_best_direction() corrects that.
    """
    image_paths = []
    for direction in range(4):
        stop(STABILISE_SEC)
        path = run_capture()
        image_paths.append(path)
        print(f"  Captured dir {direction} ({direction * 90}°) → {path}")
        if direction < 3:
            turn_right_90()     # PID-controlled (was timed)
    return image_paths

# ── RL model interface ─────────────────────────────────────────────────────────

def _score_for_direction(run_fn, image_id: str, state: list) -> float:
    nav_fn = NAV_SCORE_MAP.get(current_model)
    if nav_fn is not None:
        score = nav_fn(image_id, state)
        if score is not None:
            return score
    return float(run_fn(image_id, state))


def query_rl_model(image_paths: list[str], websocket_send_fn=None) -> list[float]:
    run_fn, _ = MODEL_MAP[current_model]
    scores    = []
    prev_path = None

    for direction, path in enumerate(image_paths):
        image_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")

        should_send, results = pipeline.process_image(
            path, prev_path, verbose=False
        )
        prev_path = path

        if not should_send:
            reason = (
                "too similar to previous"  if not results['stage_0_5']['has_significant_change'] else
                "quality too low"          if not results['stage_1']['passes'] else
                "rejected by pipeline"
            )
            print(f"  Dir {direction}: pipeline rejected ({reason}) → 0.0")
            scores.append(0.0)
            continue

        state = [
            results['stage_0_5']['change_percentage'],
            results['stage_1']['brightness'],
            results['stage_1']['saturation'],
            results['stage_1']['sharpness'],
            results['stage_1']['edge_count'],
            results['stage_1']['mean_frequency'],
            results['stage_2']['embedding_magnitude'],
            *results['embedding'],
        ]

        score = _score_for_direction(run_fn, image_id, state)
        print(f"  Dir {direction} ({direction*90}°): model={current_model} score={score:.4f}")
        scores.append(score)

        rl_decision = run_fn(image_id, state)
        print(f"  Dir {direction}: RL decision = {rl_decision}")

        if rl_decision == 1 and send_image_callback:
            import base64
            with open(path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("utf-8")
            send_image_callback(image_id, b64)

    return scores

# ── Direction selection ────────────────────────────────────────────────────────

def pick_best_direction(scores: list[float]) -> int | None:
    """
    Return the direction index with the highest score, or None if all are 0.
    Preference order for ties: forward → right → left → back.
    """
    if max(scores) == 0.0:
        return None

    best_score = max(scores)
    PREFERENCE = [0, 1, 3, 2]
    for d in PREFERENCE:
        if scores[d] == best_score:
            return d

    return int(scores.index(best_score))

# ── Orientation correction ────────────────────────────────────────────────────

def face_best_direction(best_dir: int, current_offset: int = 3):
    """
    Rotate to face best_dir from current_offset × 90° clockwise.
    Turns are PID-controlled via pid_motion.turn_right_90().
    """
    right_turns_needed = (best_dir - current_offset) % 4
    print(f"  Facing dir {current_offset*90}° → want dir {best_dir*90}°"
          f" → {right_turns_needed} right turn(s)")
    for _ in range(right_turns_needed):
        turn_right_90()     # PID-controlled (was timed)
    stop(STABILISE_SEC)

# ── Main loop ─────────────────────────────────────────────────────────────────

def main():
    global is_navigating
    print(f"Starting navigation loop  (model: {current_model})")
    reset_distance()    # zero the odometer at session start
    cycle = 0
    try:
        while True:
            is_navigating = True
            cycle += 1
            print(f"\n=== Cycle {cycle} ===")

            # Phase 1: 360° survey
            print("Surveying...")
            image_paths = survey_360()

            # Phase 2: RL inference
            print("Running RL inference...")
            scores = query_rl_model(image_paths)
            print(f"  Scores: {[f'{s:.4f}' for s in scores]}  (model: {current_model})")

            best_dir = pick_best_direction(scores)

            if best_dir is None:
                print("  No viable direction — waiting and re-surveying.")
                stop(2.0)
                continue

            print(f"  Best direction: {best_dir} ({best_dir * 90}°)")

            # Phase 3: orient + drive  (both PID-controlled via pid_motion.py)
            face_best_direction(best_dir, current_offset=3)
            drive_forward(DRIVE_FWD_SEC)
            print(f"  Odometer: {get_total_distance_cm():.1f} cm total")

    except KeyboardInterrupt:
        print("\nInterrupted by user.")
    finally:
        is_navigating = False
        pi.write(STBY, 0)
        pi.set_PWM_dutycycle(PWMA, 0)
        pi.set_PWM_dutycycle(PWMB, 0)
        pi.stop()
        print("Robot safely disarmed.")

if __name__ == "__main__":
    main()
