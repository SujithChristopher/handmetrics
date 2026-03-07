import cv2
import numpy as np
import mediapipe as mp
import os
import urllib.request
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

class HandDetector:
    """
    Handles automatic Left/Right hand detection using modern MediaPipe Tasks API.
    """
    MODEL_URL = 'https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task'
    MODEL_PATH = os.path.join(os.path.dirname(__file__), 'hand_landmarker.task')

    def __init__(self):
        self.landmarker = None
        self._initialize_model()

    def _initialize_model(self):
        """Download model if it doesn't exist and initialize landmarker."""
        if not os.path.exists(self.MODEL_PATH):
            print(f"Downloading MediaPipe Hand Landmarker model...")
            try:
                urllib.request.urlretrieve(self.MODEL_URL, self.MODEL_PATH)
                print("Model downloaded successfully.")
            except Exception as e:
                print(f"Failed to download model: {e}")
                return

        try:
            base_options = python.BaseOptions(model_asset_path=self.MODEL_PATH)
            options = vision.HandLandmarkerOptions(
                base_options=base_options,
                num_hands=1,
                min_hand_detection_confidence=0.5
            )
            self.landmarker = vision.HandLandmarker.create_from_options(options)
        except Exception as e:
            print(f"Failed to initialize HandLandmarker: {e}")

    def detect_hand_side(self, bgr_image: np.ndarray) -> str:
        """
        Detects whether the image contains a Left or Right hand.
        Expects a BGR image array.
        Returns: 'Left', 'Right', or 'Unknown'
        """
        if bgr_image is None or self.landmarker is None:
            return "Unknown"

        try:
            # MediaPipe expects RGB images
            rgb_image = cv2.cvtColor(bgr_image, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_image)
            
            detection_result = self.landmarker.detect(mp_image)

            if detection_result.handedness:
                # MediaPipe Tasks API returns 'Left' or 'Right'
                # Note: HandLandmarker correctly models physical hands
                handedness = detection_result.handedness[0][0].category_name
                return handedness
                
            return "Unknown"
        except Exception as e:
            print(f"Error in hand detection: {e}")
            return "Unknown"
