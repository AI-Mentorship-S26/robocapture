To run the website and raspberry pi, there needs to be several elements you need to take care of.

First, clone the repository, by opening a new folder, doing "git init", and then doing "git clone https://github.com/AI-Mentorship-S26/robocapture".

## Hardware Readiness

Second, you'll need to set up the robot. For this, you'll need quite a numerous number of hardware components. First, you'll need a Raspberry Pi. In our case we used a model 4, so you'd need at least that model. Second, you'll need two FIT 0458 Motors + Encoders, which you can buy off something such as Digikey or Robotshop.

You'll also need a motor driver to control the motors, in our case we used a Dual TB6612FNG motor driver. Finally, you'll need any kind of camera that can interface with a Raspberry Pi, in our case we used a "picamera2". You'll also need two wheels to fit on the shafts of the motors. The wheels I believe were "TT wheels", they'll look yellow basically.

Now the fun part: wiring the robot! You've got several components to wire here.

First, let's take the motor driver and motors, and connect them. First, youll see pins "AO1" and "AO2". That's where the first motor will connect - one wire (preferably the red one) connects to AO1, and the second wire (preferably the black one) connects to AO2. Same with the second motor, BO1 connects to the red wire of the 2nd motor, and BO2 connects to that motor's black wire.

Next, let's connect the Raspberry Pi to the motor driver. Connect any 5V pin from the Raspberry Pi to the VCC pin on the Motor Driver. Connect any Raspberry Pi's GND pin to the GND pin on the motor driver as well. This will allow the Pi to "power" the driver essentially.

Next, there's multiple 'control' pins on the driver that need to interface with the Pi. These are the "PWM A", "PWM B", "AIN1", "AIN2", "BIN1", and "BIN2" pins. These should be connected directly to the Raspberry Pi, specifically certain pins. You may want to look at the pinout for the Pi here. Here are the pinout mappings:

- driver PWM A pin: GPIO 12 
- driver PWM B pin: GPIO 13
- driver AIN1 pin: GPIO 6 
- driver AIN2 pin: GPIO 5
- driver BIN1: GPIO 16 
- driver BIN2: GPIO 26

Finally, for the driver there’s a STNDBY pin, you want to connect that to the VCC pin. The reason for this is because it basically has 2 settings: powered ‘off’ when it has 0 voltage, and powered ‘on’ when it received ‘high’ voltage. We want it powered on obviously, so we sent it max voltage.
Now, let’s connect the motor encoders. First, you should note that they take power around 5 volts. So, you should connect their power pins (the red wires) to either any remaining 5V pins on the pi, or the VCC pin on the motor driver. Next, connect their ground pins (the black wires) to any GND pins on either the Pi or the motor driver.

Now there are green and blue wires on both of the encoders - these are what the Pi ‘reads’ to see the current encoder values. Connect them to the pi like this:

- right encoder green pin: GPIO 17 
- right encoder blue pin: GPIO 27 
- left encoder green pin: GPIO 25 
- left encoder blue pin: GPIO 24

Now every component is wired properly, but we still need a battery to actually power the whole thing. 

You’ll need a battery roughly in the range of 6-9 volts, I’d recommend just using a 2S battery that’s 7.4V. As for the specific battery, the one I used is this: https://www.amazon.com/HRB-2200mAh-Battery-Traxxas-Revo/dp/B07NRM7HFZ/, it has a pretty good battery life so I’d recommend it. You also probably want to buy a TRX female to XT 60 connector or some other kinda connector so you can connect the battery to a LiPo charger.

Now as for actually powering it, you want to connect the battery power wire to the VM pin on the motor driver, as basically that is the power directed to drive the motors. You then want to connect the battery’s ground wire to the ground of the raspberry pir or motor driver (i’d recommend the motor driver).

Now one issue remains: powering the Raspberry Pi. We can’t direectly connect the battery to it because the battery provides 7.4V while the Pi can only take 5 volts, so we need a buck converter to reduce the voltage. For this I used this product: https://www.amazon.com/Solu-Adjustable-Step-down-Converter-Voltmeter/dp/B00VWL41TM?ie=UTF8, it worked fairly decent.

First thing you want to do is connect the battery’s power wire (in parallel as another wire goes to the VM pin on the driver) to the buck converter’s VIN+ pin, and connect the batterys ground wire (once again in parallel to its other ground wire) to the buck converter’s VIN- pin. Once you do that you should see the buck converter display a LED in red, that is its current output voltage. You want to screw one the designated screw (or do whatever you need to to change the voltage on your buck converter) until it reads 5 volts. Then, you can connect the VOUT+ pin to a 5V pin on the Pi, and connect the VOUT- pin to a GND pin on the Pi.
Boom! You’re all set hardware wise. 

You now need to put it all in a robot. What I did for that was head to the makerspace and grab old robot chassis that were used for combat bots but were thrown away, you can probably do something like that.

Finally, just connect the camera to the pi. If you use a picam camera, it’s as easy as just connecting the ribbon to one of the designated areas on the board.

## Raspberry Pi Software Setup

First, you need to setup the Raspberry Pi. Make sure you have an sd card for this you can plug into the Pi (usually when you purchase one it comes with an sd card). Then, install the Raspberry Pi OS onto it as normal (i’d recommend installing a desktop on it). 

Next you need to connect you Pi to wifi. I’d recommend having a HDMI to micro HDMI cable so you can connect it to a monitor, then connect a mouse + keyboard to the pi via USB so you can access its desktop. Then, you can directly configure its wifi as if it were a laptop. You probably can’t connect it to CometNet though cause it blocks embedded devices, but any other wifi (or your hotspot if it’s really needed ) should be fair game.

Once it’s connected, create a folder on the pi and do “git init” then “git clone” as you did before. All the code pertinent to the Pi will be in the “picam” folder.

Now finally, once you connect it to wifi, take note of what IP address there is and write it down - sometimes it will change since IP addresses aren’t permanent, so take note of that.

Now you need to set up environment variables.

First, you’ll need to put a .env file in the home directory of the github repository for the Pi, and put a .env.local file in the frontend directory of the github repisotiry for the website. For the .env file, you’ll need to fill in the “SUPABASE_URL” key and the “SUPABASE_KEY” values. I obviously can’t share them here, you can also setup Supabase yourself and get these values.

For the .env.local file, you’ll need to fill in the “NEXT_PUBLIC_SUPABASE_URL” and “NEXT_PUBLIC_SUPABASE_ANON_KEY” keys. Same as above, I can’t share them but you can probably get the yourself by initializeing a supabase environment with Postgres. In the same file you also have to fill in the “NEXT_PUBLIC_PI_WS_URL” key. This will be something like ws://<ip>:<port>, but with your own values. Ip is the IP address of the Pi (which you should’ve already gotten above), and the Port should be 8765. If you change it, make sure you change it in some of the Raspberry Pi files and anywhere else we use that port number.

Finally, in the backend folder on the github there is a “appsettings.json” folder. In it you’ll find a field called “PiWebSocketUrl”. Change this to be the same value as the NEXT_PUBLIC_PI_WS_URL key discussed earlier.

Now once you’ve got this done, you’re ready to actually run the project!

## Actually running the project

First you’ll want to start the website. Navigate to the backend folder (such as by doing “cd backend”), and run the backend by doing “dotnet run”. If that fails, do “dotnet install” first. Then, navigate to the frontend folder (such as by doing “cd frontend”), and run it by doing “npm run dev”, or “npm install” if libraries haven’t been installed yet. Then, you can just navigate to “http://localhost:3000/” to access the website. 

To start the raspberry Pi server, you just go to the raspberry pi such as by ssh’ing into it (to do that, connect to the same wifi the pi is on, then in your computer’s terminal run the command “ssh <username>@<ip>” and then put your password when prompted. When settuping up your Pi ost it will require you to make the root user’s username and password, so you can just put those in), then navigate to the picam folder, and run the python server by doing “python pi_server.py” on that file. This will start the pi server, and eventually you should find it connect to the website. Then use the website as prompted, and everything should work!

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
