# robocapture

### Prerequisites
- .NET SDK
- Node.js


## Steps to run the connection between Pi, Backend and Frontend:

1. Run the Pi WebSocket server (run the command in the Pi's terminal):
python3 /home/mahd/Desktop/Robocapture/robocapture/picam/pi_server.py

2. Update this line in `appsettings.json` in the backend folder with your Pi's IP:
"PiWebSocketUrl": "ws://YOUR_PI_IP:8765"

3. Run the backend (on your system's terminal):
dotnet run

4. Run the frontend (on your system's terminal):
npm run dev

## Pi-side local dataset workflow

If you want to build a labeled dataset directly on the Pi without the frontend:

1. Capture and label images into a local CSV:
python3 picam/collect_labeled_dataset.py --count 100

This will:
- capture an image on the Pi
- compute the full 1287-value state
- prompt you to label it as `reward` or `punishment`
- append the row to `picam/datasets/labeled_dataset.csv`

2. Train all RL models on the collected dataset:
python3 picam/train_models_offline.py picam/datasets/labeled_dataset.csv

3. Inspect a saved model checkpoint if needed:
python3 picam/inspect_saved_model.py reinforce
