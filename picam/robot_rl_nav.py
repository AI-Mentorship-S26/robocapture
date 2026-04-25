"""
robot_rl_nav.py
───────────────
360-survey → RL inference → navigate loop.

HOW IT WORKS
  1. Stop and stabilise.
  2. Take a photo, turn 90° LEFT, repeat ×4  →  images[0..3]
       dir 0 = forward (original heading)
       dir 1 = 90° left
       dir 2 = 180° (behind)
       dir 3 = 90° right
  3. Pass all four images to your RL model.
  4. Pick the best direction from the returned scores.
  5. Turn to face that direction, drive forward, repeat.

TURNS  — encoder-controlled via pid_motion.py (accurate 90°)
DRIVE  — original timed set_motors approach (unchanged from original)

WIRING
  AIN1=6  AIN2=5   PWMA=12
  BIN1=16 BIN2=26  PWMB=13
  STBY=25
"""

import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
import pigpio

sys.path.insert(0, str(Path(__file__).parent))
from image_preprocessing import ImagePreprocessingPipeline
from rl_models import (
    run_random,            update_random,            nav_score_random,
    run_contextual_bandit, update_contextual_bandit,  nav_score_contextual_bandit,
    run_sarsa,             update_sarsa,              nav_score_sarsa,
    run_dqn,               update_dqn,               nav_score_dqn,
    run_ppo,               update_ppo,               nav_score_ppo,
    run_reinforce,         update_reinforce,          nav_score_reinforce,
    run_aac,               update_aac,               nav_score_aac,
    run_tiny_sac,          update_tiny_sac,           nav_score_tiny_sac,
)

# ── Encoder turns only — pid_motion owns its own pigpio instance ───────────────
from pid_motion import turn_left_90

is_navigating = False

send_image_callback = None
def set_send_callback(callback):
    global send_image_callback
    send_image_callback = callback

# ── Configuration ──────────────────────────────────────────────────────────────

DRIVE_SPEED   = 200
TURN_SPEED    = 150
DRIVE_FWD_SEC = 1.5
STABILISE_SEC = 0.3

# ── Pin definitions ────────────────────────────────────────────────────────────

AIN1, AIN2, PWMA = 6,  5,  12
BIN1, BIN2, PWMB = 16, 26, 13
STBY             = 25

# ── RL model registry ─────────────────────────────────────────────────────────

MODEL_MAP = {
    "random":            (run_random,            update_random),
    "contextual_bandit": (run_contextual_bandit,  update_contextual_bandit),
    "sarsa":             (run_sarsa,              update_sarsa),
    "dqn":               (run_dqn,               update_dqn),
    "ppo":               (run_ppo,               update_ppo),
    "reinforce":         (run_reinforce,          update_reinforce),
    "aac":               (run_aac,               update_aac),
    "tiny_sac":          (run_tiny_sac,           update_tiny_sac),
}

NAV_SCORE_MAP = {
    "random":            nav_score_random,
    "contextual_bandit": nav_score_contextual_bandit,
    "sarsa":             nav_score_sarsa,
    "dqn":               nav_score_dqn,
    "ppo":               nav_score_ppo,
    "reinforce":         nav_score_reinforce,
    "aac":               nav_score_aac,
    "tiny_sac":          nav_score_tiny_sac,
}

current_model = "sarsa"
pipeline      = ImagePreprocessingPipeline()

def set_current_model(model_name: str):
    global current_model
    if model_name not in MODEL_MAP:
        print(f"  [WARN] Unknown model '{model_name}' — keeping '{current_model}'")
        return
    current_model = model_name
    print(f"  [Nav] Active model switched to: {current_model}")

# ── pigpio init — owns drive/stop only, pid_motion owns encoder turns ──────────

pi = pigpio.pi()
if not pi.connected:
    raise RuntimeError("Cannot connect to pigpiod — run 'sudo pigpiod' first.")

for pin in [AIN1, AIN2, PWMA, BIN1, BIN2, PWMB, STBY]:
    pi.set_mode(pin, pigpio.OUTPUT)

pi.set_PWM_range(PWMA, 255);      pi.set_PWM_range(PWMB, 255)
pi.set_PWM_frequency(PWMA, 1000); pi.set_PWM_frequency(PWMB, 1000)
pi.write(STBY, 1)

# ── Camera ─────────────────────────────────────────────────────────────────────

_SCRIPT_DIR     = os.path.dirname(os.path.abspath(__file__))
_CAPTURE_SCRIPT = os.path.join(_SCRIPT_DIR, "capture_once.py")

# ── Motor control — original unchanged from old robot_rl_nav.py ───────────────

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

def drive_forward(duration: float = DRIVE_FWD_SEC):
    run_command(DRIVE_SPEED, DRIVE_SPEED, duration, "Forward")

# ── Camera capture ─────────────────────────────────────────────────────────────

def run_capture() -> str:
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

# ── 360° survey — turns LEFT each step ────────────────────────────────────────
#
# Direction mapping (left-turn survey):
#   dir 0 = forward (original heading)
#   dir 1 = 90° left
#   dir 2 = 180° (behind)
#   dir 3 = 270° left = 90° right

def survey_360() -> list[str]:
    image_paths = []
    for direction in range(4):
        stop(STABILISE_SEC)
        path = run_capture()
        image_paths.append(path)
        print(f"  Captured dir {direction} ({direction * 90}° left) → {path}")
        if direction < 3:
            turn_left_90()      # encoder-controlled
    return image_paths

# ── RL model interface ─────────────────────────────────────────────────────────

def _score_for_direction(run_fn, image_id: str, state: list) -> float:
    nav_fn = NAV_SCORE_MAP.get(current_model)
    if nav_fn is not None:
        score = nav_fn(image_id, state)
        if score is not None:
            return score
    return float(run_fn(image_id, state))


def query_rl_model(image_paths: list[str]) -> list[float]:
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
        print(f"  Dir {direction} ({direction*90}° left): model={current_model} score={score:.4f}")
        scores.append(score)

    return scores

# ── Direction selection ────────────────────────────────────────────────────────

def pick_best_direction(scores: list[float]) -> int | None:
    if max(scores) == 0.0:
        return None

    best_score = max(scores)
    PREFERENCE = [0, 1, 3, 2]   # forward → left → right → back
    for d in PREFERENCE:
        if scores[d] == best_score:
            return d

    return int(scores.index(best_score))

# ── Orientation correction ─────────────────────────────────────────────────────
#
# After survey_360() robot has turned left 3 times (270° left from start).
# Additional left turns needed = (best_dir - 3) % 4

def face_best_direction(best_dir: int):
    left_turns_needed = (best_dir - 3) % 4
    print(f"  Need {left_turns_needed} more left turn(s) to face dir {best_dir}")
    for _ in range(left_turns_needed):
        turn_left_90()      # encoder-controlled
    stop(STABILISE_SEC)

# ── Main loop ─────────────────────────────────────────────────────────────────

def main():
    global is_navigating
    print(f"Starting navigation loop  (model: {current_model})")
    cycle = 0
    try:
        while True:
            is_navigating = True
            cycle += 1
            print(f"\n=== Cycle {cycle} ===")

            print("Surveying...")
            image_paths = survey_360()

            print("Running RL inference...")
            scores = query_rl_model(image_paths)
            print(f"  Scores: {[f'{s:.4f}' for s in scores]}  (model: {current_model})")

            best_dir = pick_best_direction(scores)

            if best_dir is None:
                print("  No viable direction — waiting and re-surveying.")
                stop(2.0)
                continue

            print(f"  Best direction: {best_dir}")

            face_best_direction(best_dir)
            drive_forward(DRIVE_FWD_SEC)

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
