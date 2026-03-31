"""
Local testing script for image preprocessing pipeline
Tests all stages with a synthetic test image
"""

import sys
from pathlib import Path
import numpy as np
import cv2
import json

# Add parent directory to path (assumes image_preprocessing.py is in parent)
sys.path.insert(0, str(Path(__file__).parent.parent))

from image_preprocessing import ImagePreprocessingPipeline

def create_test_image(filename="test_image.jpg", quality="good"):
    """
    Create synthetic test images with different quality levels
    """
    print(f"\n📸 Creating '{quality}' test image...")
    
    if quality == "good":
        img = np.ones((540, 960, 3), dtype=np.uint8) * 120
        cv2.rectangle(img, (50, 50), (200, 200), (0, 255, 0), -1)
        cv2.circle(img, (400, 300), 100, (255, 0, 0), -1)
        cv2.rectangle(img, (600, 100), (900, 400), (0, 0, 255), -1)
        noise = np.random.normal(0, 15, img.shape).astype(np.uint8)
        img = cv2.add(img, noise)
        
    elif quality == "dark":
        img = np.ones((540, 960, 3), dtype=np.uint8) * 30
        cv2.rectangle(img, (50, 50), (200, 200), (50, 100, 50), -1)
        cv2.circle(img, (400, 300), 100, (100, 50, 50), -1)
        
    elif quality == "blurry":
        img = np.ones((540, 960, 3), dtype=np.uint8) * 120
        cv2.rectangle(img, (50, 50), (200, 200), (0, 255, 0), -1)
        cv2.circle(img, (400, 300), 100, (255, 0, 0), -1)
        for _ in range(5):
            img = cv2.GaussianBlur(img, (15, 15), 0)
        
    elif quality == "empty":
        img = np.ones((540, 960, 3), dtype=np.uint8) * 128
    
    cv2.imwrite(filename, img)
    print(f"✓ Saved: {filename}")
    return filename


def main():
    print("\n" + "="*70)
    print("LOCAL PREPROCESSING PIPELINE TEST")
    print("="*70)
    
    print("\n🔧 Initializing preprocessing pipeline...")
    pipeline = ImagePreprocessingPipeline(
        brightness_min=40,
        brightness_max=200,
        blur_threshold=50,
        change_threshold=5.0
    )
    print("✓ Pipeline initialized")
    
    print("\n" + "="*70)
    print("TEST 1: Good Quality Image")
    print("="*70)
    good_img = create_test_image("test_good.jpg", quality="good")
    should_send, results = pipeline.process_image(good_img, verbose=True)
    
    print(f"\n{'='*70}")
    if should_send:
        print("✅ RESULT: IMAGE PASSED")
    else:
        print("❌ RESULT: IMAGE REJECTED")
    print(f"{'='*70}")
    
    with open("test_result_good.json", 'w') as f:
        json.dump({
            "test": "good_image",
            "passed": should_send,
            "brightness": float(results['stage_1']['brightness']),
            "sharpness": float(results['stage_1']['sharpness'])
        }, f, indent=2)
    
    print("\n✓ Test complete!")


if __name__ == "__main__":
    main()