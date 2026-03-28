# robocapture

### Prerequisites
- .NET SDK
- Node.js


## Steps to run the connection between Pi, Backend and Frontend:

1. Run the Pi WebSocket server (run the command in the Pi's terminal):
python3 /home/mahd/Desktop/Robocapture/robocapture/picam/captures/pi_server.py

2. Update this line in `appsettings.json` in the backend folder with your Pi's IP:
"PiWebSocketUrl": "ws://YOUR_PI_IP:8765"

3. Run the backend (on your system's terminal):
dotnet run

4. Run the frontend (on your system's terminal):
npm run dev
