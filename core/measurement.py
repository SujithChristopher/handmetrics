from typing import Optional, Dict, Tuple
import numpy as np
import cv2

# measurement.py: Core business logic for camera-orientation-agnostic pixel→cm conversion.
#
# Instead of a simple "average edge length / tag_size" scalar ratio, we compute a full
# planar homography H (3×3, pixel-space → cm-space) from the AprilTag's four detected
# corners.  This makes all measurements correct even when the camera is tilted or rotated
# relative to the hand plane — no camera matrix or distortion coefficients needed.
#
# Usage:
#   calc = MeasurementCalculator()
#   calc.calibrate_from_apriltag(corners)       # corners: (4,2) float32 array
#   x_cm, y_cm = calc.pixel_point_to_cm(u, v)  # map one pixel
#   dist = calc.pixel_distance_to_cm(u1,v1, u2,v2)  # Euclidean in cm-space


class MeasurementCalculator:
    """
    Business Logic: Handles AprilTag-based calibration and pixel-to-metric conversions.
    Separated from the UI to allow for headless measurement processing or
    alternative visualization frontends.

    Calibration uses a planar homography computed from the four corners of the detected
    AprilTag quadrilateral.  This is perspective-correct for any camera orientation.
    """

    def __init__(self):
        self.apriltag_size_m: float = 0.07      # Default 7 cm
        self.apriltag_size_cm: float = 7.0

        # Homography matrix (pixel coords → cm coords), set after calibration
        self.homography: Optional[np.ndarray] = None

        # Raw detected corners kept so we can recompute H if tag size changes
        self._raw_corners: Optional[np.ndarray] = None

        # Display-only approximation (kept for UI readouts and backward compat)
        self.pixels_per_cm: Optional[float] = None

        self.scale_calibrated: bool = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_apriltag_size(self, size_m: float) -> bool:
        """Update AprilTag physical size and recompute homography if already calibrated."""
        if size_m <= 0:
            return False

        self.apriltag_size_m = size_m
        self.apriltag_size_cm = size_m * 100.0

        # Recompute if we already have raw corners
        if self._raw_corners is not None:
            return self._compute_homography(self._raw_corners)
        return False

    def calibrate_from_apriltag(self, corners: np.ndarray) -> bool:
        """
        Calibrate using the four detected AprilTag corners.

        Parameters
        ----------
        corners : np.ndarray, shape (4, 2)
            Pixel coordinates of the four tag corners in the order returned by
            OpenCV ArUco (TL → TR → BR → BL).

        Returns
        -------
        bool : True if calibration succeeded.
        """
        if corners is None or len(corners) != 4:
            return False

        self._raw_corners = corners.astype(np.float32)
        return self._compute_homography(self._raw_corners)

    def pixel_point_to_cm(self, u: float, v: float) -> Tuple[float, float]:
        """
        Map a single pixel coordinate (u, v) → (x_cm, y_cm) via homography.

        Raises RuntimeError if not yet calibrated.
        """
        if self.homography is None:
            raise RuntimeError("MeasurementCalculator not calibrated yet.")

        pt = np.array([u, v, 1.0], dtype=np.float64)
        mapped = self.homography @ pt
        w = mapped[2]
        return float(mapped[0] / w), float(mapped[1] / w)

    def pixel_distance_to_cm(
        self,
        u1: float, v1: float,
        u2: float, v2: float,
    ) -> float:
        """
        Euclidean distance in cm between two pixel points, corrected for perspective.

        Parameters
        ----------
        u1, v1 : pixel coordinates of point 1
        u2, v2 : pixel coordinates of point 2
        """
        if not self.scale_calibrated or self.homography is None:
            return 0.0

        x1, y1 = self.pixel_point_to_cm(u1, v1)
        x2, y2 = self.pixel_point_to_cm(u2, v2)
        return float(np.hypot(x2 - x1, y2 - y1))

    def get_scale_info(self) -> Dict:
        """Get calibration information for display / export."""
        return {
            'calibrated': self.scale_calibrated,
            'homography_available': self.homography is not None,
            # pixels_per_cm kept as a display-only approximation
            'pixels_per_cm': self.pixels_per_cm,
            'apriltag_size_cm': self.apriltag_size_cm,
            'apriltag_size_m': self.apriltag_size_m,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _compute_homography(self, corners: np.ndarray) -> bool:
        """
        Build a homography from pixel corners → real-world cm corners.

        OpenCV ArUco returns corners in order: TL, TR, BR, BL.
        We map these to the four corners of a square with side = apriltag_size_cm.

            TL = (0,                0)
            TR = (apriltag_size_cm, 0)
            BR = (apriltag_size_cm, apriltag_size_cm)
            BL = (0,                apriltag_size_cm)
        """
        try:
            s = self.apriltag_size_cm
            dst_cm = np.array(
                [[0, 0], [s, 0], [s, s], [0, s]],
                dtype=np.float32,
            )

            H, mask = cv2.findHomography(corners, dst_cm)
            if H is None:
                return False

            self.homography = H

            # Derive a display-only pixels_per_cm from mean edge length
            edge_lengths = []
            for i in range(4):
                p1 = corners[i]
                p2 = corners[(i + 1) % 4]
                edge_lengths.append(float(np.linalg.norm(p2 - p1)))
            avg_edge_px = float(np.mean(edge_lengths))
            self.pixels_per_cm = avg_edge_px / s

            self.scale_calibrated = True
            return True

        except Exception as e:
            print(f"Homography calibration error: {e}")
            return False
