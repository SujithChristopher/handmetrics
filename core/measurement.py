from typing import Optional, Dict
import numpy as np

# measurement.py: This file contains the core business logic for calculating measurements.
# It is designed to be independent of any specific UI framework, allowing for
# flexible integration into different frontends or headless processing.
class MeasurementCalculator:
    """
    Business Logic: Handles camera calibration and pixel-to-metric conversions.
    Separated from the UI to allow for headless measurement processing or 
    alternative visualization frontends.
    """
    """Calculate measurements using AprilTag as reference."""

    APRILTAG_SIZE_CM = 7.0  # 7x7 cm marker

    def __init__(self):
        self.pixels_per_cm: Optional[float] = None
        self.scale_calibrated = False

    def calibrate_from_apriltag(self, corners: np.ndarray) -> bool:
        """
        Calibrate pixel-to-cm ratio from AprilTag corners.

        AprilTag has 4 corners. We calculate the average edge length.
        """
        if corners is None or len(corners) != 4:
            return False

        try:
            # Calculate all 4 edge lengths
            distances = []
            for i in range(4):
                p1 = corners[i]
                p2 = corners[(i + 1) % 4]
                dist = np.linalg.norm(p2 - p1)
                distances.append(dist)

            # Average edge length in pixels
            avg_pixels = np.mean(distances)

            # Calculate pixels per cm
            # AprilTag is 7x7 cm, so edge is 7 cm
            self.pixels_per_cm = avg_pixels / self.APRILTAG_SIZE_CM
            self.scale_calibrated = True

            return True
        except Exception as e:
            print(f"Calibration error: {e}")
            return False

    def pixel_distance_to_cm(self, pixel_distance: float) -> float:
        """Convert pixel distance to cm."""
        if not self.scale_calibrated or self.pixels_per_cm is None:
            return 0.0
        return pixel_distance / self.pixels_per_cm

    def get_scale_info(self) -> Dict:
        """Get calibration information."""
        return {
            'calibrated': self.scale_calibrated,
            'pixels_per_cm': self.pixels_per_cm,
            'apriltag_size_cm': self.APRILTAG_SIZE_CM
        }
