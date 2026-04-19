from picamzero import Camera
from pathlib import Path
from datetime import datetime
import sys
import cv2

try:
    base_folder = Path(__file__).parent / "captures"
    base_folder.mkdir(exist_ok=True)

    filename = base_folder / f"image_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.jpg"

    cam = Camera()
    cam.take_photo(str(filename))

    img = cv2.imread(str(filename))
    if img is not None:
        cv2.imwrite(str(filename), cv2.rotate(img, cv2.ROTATE_180))

    print(str(filename.resolve()))
    sys.exit(0)

except Exception as e:
    print(f"ERROR: {e}", file=sys.stderr)
    sys.exit(1)
