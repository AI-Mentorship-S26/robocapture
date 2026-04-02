import sys
import time
import cv2
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parts))
from image_preprocessing import ImagePreprocessingPipeline

def getimage(filename):
    cap = cv2.VideoCapture(0)
    time.sleep(0.5) 
    ret, frame = cap.read()
    cap.release()
    
    if ret:
        cv2.imwrite(filename, frame)
        return filename
    return None

# Initialize pipeline
pipeline = ImagePreprocessingPipeline()

previous_image = None
done = False
frame_counter = 0  # <--- Added a simple counter

while not done:
    
    # wait 5 seconds
    time.sleep(5)
    
    # Alternate between "frame_0.jpg" and "frame_1.jpg"
    current_filename = f"frame_{frame_counter % 2}.jpg"
    
    # next image = getimage()
    next_image = getimage(current_filename)
    
    if next_image is None:
        print("Camera failed to capture, trying again...")
        continue
        
    # should send , results = process image(next image, previous image, verbose = True)
    should_send, results = pipeline.process_image(next_image, previous_image, verbose=True)
    
    if should_send:
        print("\n PASSED - Ready to send")
    else:
        print("\n REJECTED - TOO poor quality")
        
    # previous image = next_image
    previous_image = next_image
    frame_counter += 1  # <--- Increment the counter