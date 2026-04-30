# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Is

RoboCapture is a Raspberry Pi robot that autonomously explores its environment. It rotates 360°, captures images at 4 headings, scores each direction using contrastive MobileNetV2 embeddings, moves toward the most visually interesting direction, and streams images to a web dashboard in real time.

The repo has three independent parts:

- `picam/` — Python code that runs on the Raspberry Pi
- `backend/` — C# ASP.NET WebSocket bridge (runs on the developer's machine)
- `frontend/` — Next.js dashboard (runs on the developer's machine)

**`picam/` cannot run on Windows** — it depends on `pigpio`/`picamzero` which are Linux/Pi-only.

---

## Commands

### Frontend (Next.js)

```bash
cd frontend
npm run dev       # dev server at localhost:3000
npm run build     # production build
npm run lint      # ESLint
```

### Backend (C# — runs on developer machine)

```bash
cd backend
dotnet run        # WebSocket bridge on http://localhost:5081
```

The Pi IP is configured via `PiWebSocketUrl` in `appsettings.json` (default: `ws://172.20.10.12:8765`).

### Pi-side (run on the Raspberry Pi)

```bash
sudo pigpiod                                    # must run first — starts pigpio daemon
python3 picam/pi_server.py                      # autonomous loop + WebSocket server on port 8765
python3 picam/capture_once.py                   # test camera capture only
python3 picam/ultrasonic.py                     # test HC-SR04 distance readings
python3 picam/inspect_saved_model.py            # inspect a saved RL checkpoint
```

### Offline dataset tooling (run from repo root, works on Windows with `.venv-1`)

```bash
# Capture and label images interactively on the Pi
python3 picam/collect_labeled_dataset.py --count 100

# Bulk-import phone/external images (folder name must contain "reward" or "punishment")
.venv-1/Scripts/python picam/import_labeled_images.py rewards/ punishments/
.venv-1/Scripts/python picam/import_labeled_images.py rewards/ punishments/ --dry-run

# Train all models offline against the dataset
.venv-1/Scripts/python picam/train_models_offline.py picam/datasets/labeled_dataset.csv

# Plot rolling accuracy (window=20) for each model
.venv-1/Scripts/python picam/plot_model_accuracy.py
.venv-1/Scripts/python picam/plot_model_accuracy.py --window 30

# Train/test holdout evaluation (recommended: --train-size 451 leaves 100 test images)
.venv-1/Scripts/python picam/plot_model_accuracy.py --holdout --train-size 451

# Epoch sweep across models
.venv-1/Scripts/python picam/plot_epoch_sweep.py
```

---

## Architecture

### Connection topology

```text
Pi (port 8765) ←→ C# backend (port 5081) ←→ Next.js frontend (port 3000)
```

The frontend **never connects directly to the Pi**. It connects to `ws://localhost:5081/ws` (the C# backend), which maintains a persistent WebSocket to the Pi and forwards messages bidirectionally. The backend reconnects to the Pi automatically every 2 seconds on failure.

### Pi Side (`picam/`)

**`pi_server.py`** is the Pi entry point. On startup it:

1. Starts a navigation thread running `robot_rl_nav.main()`
2. Serves a WebSocket on port 8765

WebSocket commands it accepts:

- `"captureImage"` → capture, preprocess, run RL model, send back base64 JPEG or `no_send`
- `"captureDatasetImage"` → capture and analyze without RL decision; awaits `datasetLabel:ID:reward/punishment` or `datasetSkip:ID`
- `"setModel:NAME"` → switch active RL model (also switches the nav loop model)
- `"reward:IMAGE_ID"` / `"punishment:IMAGE_ID"` → update the active RL model
- `"startNavigation"` / `"stopNavigation"` → start/stop the autonomous nav loop

**`robot_rl_nav.py`** owns the autonomous loop:

1. Stop and stabilise
2. `survey_and_score()` — capture at 4 headings (90° left turns), run each through the preprocessing pipeline, score each direction with the active RL model
3. `pick_best_direction()` — highest score wins; forward preferred on ties
4. `face_best_direction()` — turn to face the chosen heading
5. `drive_forward_with_stop(DRIVE_FWD_SEC, _obstacle_ahead)` — drive forward, polling the HC-SR04 ultrasonic sensor every 50 ms; stops early if an obstacle is within `STOP_DISTANCE_CM` (25 cm) and re-surveys

Images from the autonomous loop are forwarded to the frontend via a thread-safe asyncio queue: `robot_rl_nav` calls `send_image_callback` → `_nav_callback` in `pi_server.py` uses `loop.call_soon_threadsafe(queue.put_nowait, ...)` → `forward_nav_images()` coroutine sends them over WebSocket.

**`pid_motion.py`** is the single motor+encoder module. Do not import other motor files alongside it. Actual GPIO pin assignments (BCM):

- Motors: AIN1=6, AIN2=5, PWMA=12, BIN1=16, BIN2=26, PWMB=13
- Left encoder: A=25, B=24
- Right encoder: A=17, B=27
- HC-SR04 ultrasonic: TRIG=23, ECHO=22
- Free pins available for new sensors: GPIO 4, 18

**`image_preprocessing.py`** runs a 4-stage pipeline producing a **1287-float state vector**: `[change_pct, brightness, saturation, sharpness, edge_count, mean_freq, embedding_magnitude, *embedding_1280]`. The 1280-float embedding comes from MobileNetV2.

**`collect_labeled_dataset.py`** exposes `analyze_image`, `build_dataset_row`, `append_dataset_row`, and `ensure_dataset_file` — imported by both `pi_server.py` (for live dataset capture mode) and `import_labeled_images.py` (for bulk import).

### Model Object Pattern (`picam/model_objects/`)

Use `sarsa_object.py` as the canonical reference. Every model object exposes:

```python
class XObject:
    def __init__(self):
        self.history = {}           # {image_id: (state, action)} — bridges async reward gap
        self.checkpoint_path = model_file("name", ".ext")
        self.load()

    def choose_action(self, state: list) -> int: ...
    def record(self, image_id, state, action): ...
    def update(self, image_id, reward): ...   # called when reward arrives from frontend
    def save(self): ...
    def load(self): ...

x_object = XObject()   # module-level singleton imported by rl_models.py
```

`rl_models.py` is the thin dispatch layer: `run_X(image_id, state) → int` calls `choose_action` + `record`; `update_X(image_id, reward)` calls `update`. Adding a model requires both functions in `rl_models.py` plus a `nav_score_X` function for navigation scoring, then registration in `MODEL_MAP`/`NAV_SCORE_MAP` in both `pi_server.py` and `robot_rl_nav.py`.

`persistence.py` provides `save/load_pickle` (tabular models) and `save/load_torch` (neural models). All checkpoints go to `picam/saved_models/`.

### Backend (`backend/`)

Single-file C# minimal API (`Program.cs`). Key behaviour:

- Maintains one persistent `ClientWebSocket` to the Pi; auto-reconnects every 2s on failure
- Accepts one frontend WebSocket at `/ws` at a time (`frontendSocket` global — single-client design)
- Forwards all recognised command strings to the Pi; forwards all Pi messages to the frontend
- Sends `{ type: "pi_status", connected: bool }` to the frontend when Pi connection changes

### Frontend (`frontend/`)

Next.js app with TypeScript, Tailwind v4, Supabase auth.

`app/dashboard/page.tsx` is the main client component. Key state:

- `rewardData` — rolling 20-image approval rate chart; seeded from `image_vectors` table on mount, updated by `actionWindowRef` on each `+R`/`-P` click
- `currentImageSource` — `"autonomous"` | `"manual"`; autonomous images are auto-uploaded to Supabase storage without requiring a reward click
- `captureMode` — `"live"` | `"dataset"`; switches the Pi-side capture command between `captureImage` and `captureDatasetImage`

Supabase resources used:

- Storage bucket `robocapture-images`: `{user_id}/{image_id}.jpg`
- Table `image_vectors`: columns `user_id`, `image_id`, `label` (1/-1), `rl_model`, `embedding` (pgvector), `features` (JSONB), `created_at`

---

## Key Design Constraints

- **Async reward timing**: `reward:/punishment:` messages arrive from the frontend long after `run_X` returns. The `history` dict in each model object bridges this gap — `record()` saves `(state, action)` keyed by `image_id`; `update()` retrieves and deletes it.
- **1287-float state vector**: Fixed shape across all models and the dataset CSV. Any new model must accept exactly this input.
- **No next_state available**: All models use terminal-transition approximations (1-step Monte Carlo). Do not add next-state logic without restructuring the reward pipeline.
- **CPU-bound pipeline in async context**: `pipeline.process_image` runs MobileNetV2 inference synchronously. If ever called from the asyncio event loop directly (not from the nav thread), dispatch via `loop.run_in_executor`.
- **Single frontend client**: The C# backend holds `frontendSocket` as a plain global — it only supports one connected browser tab at a time.
- **`import_labeled_images.py` specifics**: Uses `LowLevelImageFilter` and `SemanticFeatureExtractor` directly (not the full `ImagePreprocessingPipeline`) and EXIF-transposes images. Sets `change_pct=100.0` for all rows. Requires `opencv-python` (`pip install opencv-python`) in addition to the standard picam deps.
