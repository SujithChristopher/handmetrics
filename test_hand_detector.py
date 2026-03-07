import sys
import os
import cv2
import numpy as np

# Add the project directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.hand_detector import HandDetector

def test_hand_detector():
    detector = HandDetector()
    
    # Create a dummy blank image (MediaPipe won't find a hand here)
    dummy_image = np.zeros((400, 400, 3), dtype=np.uint8)
    
    result, _ = detector.detect_hand_side(dummy_image)
    print(f"Blank image detection: {result}")
    assert result == "Unknown"
    
    print("HandDetector initialized correctly and handles empty images safely.")

if __name__ == "__main__":
    test_hand_detector()
