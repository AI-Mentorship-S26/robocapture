# Local Training From Pi Dataset

This guide explains the recommended workflow for collecting labeled images with the robot, training the RL models on a local machine, and copying the trained model files back to the Raspberry Pi.

## Recommended workflow

1. Collect images and labels on the Pi
2. Copy the dataset CSV from the Pi to your local machine
3. Train the models locally
4. Copy the updated saved model files back to the Pi
5. Restart the Pi server so it loads the new checkpoints

This is the preferred setup because local training is usually faster and easier to manage than training directly on the Pi.

## What gets saved

During dataset collection, the Pi saves labeled rows into:

```text
picam/datasets/labeled_dataset.csv
```

Each row contains:

- `image_id`
- `captured_at`
- `image_path`
- `label`
- `pipeline_would_send`
- `has_significant_change`
- `stage1_passes`
- `stage2_passes`
- `features`
- `state`

The `state` column is the full 1287-value state vector used for offline training.

## Part 1: Collect the dataset on the Pi

### Start the Pi server

On the Raspberry Pi:

```bash
cd ~/robocapture
python3 picam/pi_server.py
```

### Start the frontend

On your laptop or desktop:

```bash
cd frontend
npm install
npm run dev
```

### Use Dataset Collection mode

In the dashboard:

1. Open the live dashboard
2. Switch the capture mode to `Dataset Collection`
3. Click `Capture Dataset Image`
4. Review the returned image
5. Click `Reward` or `Punishment`
6. Repeat until you have enough labeled images

Important notes:

- In `Dataset Collection` mode, the selected RL model does not matter
- Labels are written to the Pi-local dataset CSV
- The dashboard will show the running count of saved dataset rows

## Part 2: Copy the dataset to your local machine

From your local machine, copy the dataset file from the Pi.

Example:

```bash
scp mahd@mahd-pi:~/robocapture/picam/datasets/labeled_dataset.csv ./picam/datasets/
```

If the local `picam/datasets` folder does not exist yet, create it first.

## Part 3: Train locally

From the repo root on your local machine:

```bash
python -m pip install -r requirements.txt
python picam/train_models_offline.py picam/datasets/labeled_dataset.csv --quiet-samples
```

This will train all supported models and save checkpoints into:

```text
picam/saved_models/
```

### Supported models

The offline trainer automatically discovers models that have both:

- `run_<model>()`
- `update_<model>()`

So local training stays in sync with the models defined in `picam/rl_models.py`.

## Part 4: Copy trained models back to the Pi

After training finishes, copy the saved model files back to the Pi:

```bash
scp picam/saved_models/* mahd@mahd-pi:~/robocapture/picam/saved_models/
```

This replaces the checkpoints the Pi uses at runtime.

## Part 5: Restart the Pi server

On the Pi:

```bash
cd ~/robocapture
python3 picam/pi_server.py
```

When the Pi server starts again, it will load the updated model checkpoints from `picam/saved_models`.

## Useful commands

### Inspect a saved model locally

```bash
python picam/inspect_saved_model.py reinforce
```

You can replace `reinforce` with any saved model name.

### Train with more epochs

```bash
python picam/train_models_offline.py picam/datasets/labeled_dataset.csv --epochs 3 --quiet-samples
```

### Show per-sample model updates

Remove `--quiet-samples`:

```bash
python picam/train_models_offline.py picam/datasets/labeled_dataset.csv
```

## Important cautions

- Collect and train from the same code version when possible
- If you want a completely fresh run, clear `picam/saved_models/` locally before training
- `random` and `tiny_sac` may not give meaningful results right now because they are not full learning implementations
- If local and Pi environments use very different PyTorch versions, checkpoint compatibility may become an issue

## Troubleshooting

### `ModuleNotFoundError: No module named 'pandas'`

Run:

```bash
python -m pip install -r requirements.txt
```

### Frontend does not connect to the Pi

Check:

- the Pi server is running
- the Pi IP is correct in `frontend/.env.local`
- both devices are on the same network

### Dataset mode seems affected by the selected model

It should not be. In `Dataset Collection` mode, the model selector is ignored for saving labeled dataset rows.

## Short version

1. Collect labeled images in the frontend using `Dataset Collection`
2. Copy `picam/datasets/labeled_dataset.csv` from the Pi to your laptop
3. Run local training
4. Copy `picam/saved_models/*` back to the Pi
5. Restart `picam/pi_server.py`
