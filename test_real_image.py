import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parts))

from image_preprocessing import ImagePreprocessingPipeline

pipeline = ImagePreprocessingPipeline()
should_send, results = pipeline.process_image("black.jpg", "Cute_dog.jpg", verbose=True)
print(f"\n PASSED - Ready to send" if should_send else "\n REJECTED - TOO poor quality")