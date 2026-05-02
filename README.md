To run the website and raspberry pi, there needs to be several elements you need to take care of.

First, clone the repository, by opening a new folder, doing "git init", and then doing "git clone https://github.com/AI-Mentorship-S26/robocapture".

## Hardware Readiness
Second, youll need to set up the robot. For this, you'll need quite a numerous number of hardware components. First, you'll need a Raspberry Pi. In our case we used a model 4, so you'd need at least that model. Second, you'll need two FIT 0458 Motors + Encoders, which you can buy off something such as Digikey or Robotshop. 

You'll also need a motor driver to control the motors, in our case we used a Dual TB6612FNG motor driver. Finally, you'll need any kind of camera that can interface with a Raspberry Pi, in our case we used a "picamera2". You'll also need two wheels to fit on the shafts of the motors. The wheels I believe were "TT wheels", they'll look yellow basically.

Now the fun part: wiring the robot! You've got several components to wire here.

First, let's take the motor driver and motors, and connect them. First, youll see pins "AO1" and "AO2". That's where the first motor will connect - one wire (preferably the red one) connects to AO1, and the second wire (preferably the black one) connects to AO2. Same with the second motor, BO1 connects to the red wire of the 2nd motor, and BO2 connects to that motor's black wire.

Next, let's connect the Raspberry Pi to the motor driver. Connect any 5V pin from the Raspberry Pi to the VCC pin on the Motor Driver. Connect any Raspberry Pi's GND pin to the GND pin on the motor driver as well. This will allow the Pi to "power" the driver essentially. 

Next, there's multiple 'control' pins on the driver that need to interface with the Pi. These are the "PWM A", "PWM B", "AIN1", "AIN2", "BIN1", and "BIN2" pins.

Robocapture/robocapture/picam/pi_server.py

2. Update this line in `appsettings.json` in the backend folder with your Pi's IP:
"PiWebSocketUrl": "ws://YOUR_PI_IP:8765"

h

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
