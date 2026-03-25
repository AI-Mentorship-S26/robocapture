# robocapture
Uses port 5081 (can be changed in page.tsx file in frontend folder)

3/25/2026
To test, run the following command in your the Pi's terminal:
cd /home/mahd/Desktop/Robocapture/robocapture/backend

and then the following in your local terminal:
cd frontend
npm run dev


Make sure you have already created a `.env.local` file in the frontend root folder and added this line to it:
NEXT_PUBLIC_WS_URL=ws://mahd-pi.local:5081/ws

if mahd-pi.local does not work on your network, then replace it with the Pi's current IP address:
NEXT_PUBLIC_WS_URL=ws://YOUR_PI_IP:5081/ws


Then open the page http://localhost:3000 in your browser


