from picamzero import Camera
from pathlib import Path
from datetime import datetime
import time

duration = int(input("Enter total run time in seconds: "))

interval_input = input("Enter interval between each captured image in seconds: ")

if interval_input:
    interval = int(interval_input)
else:
    interval = 5

base_folder = Path("captures")
base_folder.mkdir(exist_ok=True)

img_folder = base_folder / datetime.now().strftime("images_%Y-%m-%d_%H-%M-%S")
img_folder.mkdir(parents=True, exist_ok=True)

cam = Camera()
numPhotos = duration // interval

for count in range(1, numPhotos+1):
    filename = img_folder / f"image_{count}.jpg"
    cam.take_photo(str(filename))
    
    if count != numPhotos:
        time.sleep(interval)
    
print("Done.")