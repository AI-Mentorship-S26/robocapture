from picamzero import Camera
from pathlib import Path
from datetime import datetime
import sys

try:
    base_folder = Path("/home/mahd/Desktop/Robocapture/robocapture/picam/captures")
    base_folder.mkdir(exist_ok=True)

    filename = base_folder / f"image_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.jpg"

    cam = Camera()
    cam.take_photo(str(filename))

    print(str(filename.resolve()))
    sys.exit(0)

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)