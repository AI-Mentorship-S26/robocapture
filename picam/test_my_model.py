import sys, time, cv2
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))
from image_preprocessing import ImagePreprocessingPipeline
from rl_models import run_ppo, update_ppo

pipeline = ImagePreprocessingPipeline()
previous_image = None
frame_counter = 0

print("=== PPO Test Started. Press Ctrl+C to stop. ===")
while True:
    time.sleep(3)

    filename = f"frame_{frame_counter % 2}.jpg"
    cap = cv2.VideoCapture(0)
    time.sleep(0.3)
    ret, frame = cap.read()
    cap.release()

    if not ret:
        print("Camera failed, retrying...")
        continue
    cv2.imwrite(filename, frame)

    should_send, results = pipeline.process_image(filename, previous_image, verbose=False)
    previous_image = filename
    frame_counter += 1

    if not should_send:
        print(f"[Frame {frame_counter}] Pipeline rejected")
        continue

    state = [
        results['stage_0_5']['change_percentage'],
        results['stage_1']['brightness'],
        results['stage_1']['saturation'],
        results['stage_1']['sharpness'],
        results['stage_1']['edge_count'],
        results['stage_1']['mean_frequency'],
        results['stage_2']['embedding_magnitude'],
        *results['embedding']
    ]

    image_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    decision = run_ppo(image_id, state)
    print(f"[Frame {frame_counter}] Decision: {'SEND ✓' if decision == 1 else 'NO SEND ✗'}")

    reward = 1 if decision == 1 else -1
    update_ppo(image_id, reward)
    print(f"[Frame {frame_counter}] Model updated with reward {reward}")
