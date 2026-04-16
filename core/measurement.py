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

        # Camera Pose (relative to Tag)
        self.rvec: Optional[np.ndarray] = None
        self.tvec: Optional[np.ndarray] = None
        self.camera_matrix: Optional[np.ndarray] = None
        self.dist_coeffs: np.ndarray = np.zeros(4)
        
        # Distance to camera (z-coord of tvec)
        self.camera_distance_cm: Optional[float] = None

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

    def calibrate_from_apriltag(self, corners: np.ndarray, img_w: int = 0, img_h: int = 0) -> bool:
        """
        Calibrate using the four detected AprilTag corners.

        Parameters
        ----------
        corners : np.ndarray, shape (4, 2)
            Pixel coordinates of the four tag corners in the order returned by
            OpenCV ArUco (TL → TR → BR → BL).
        img_w, img_h : image dimensions (optional, used for pose estimation)

        Returns
        -------
        bool : True if calibration succeeded.
        """
        if corners is None or len(corners) != 4:
            return False

        self._raw_corners = corners.astype(np.float32)
        success = self._compute_homography(self._raw_corners)
        
        if success and img_w > 0 and img_h > 0:
            self._estimate_pose(self._raw_corners, img_w, img_h)
            
        return success

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

    def pixel_point_to_cm_at_height(self, u: float, v: float, h: float) -> Tuple[float, float]:
        """
        Map a single pixel coordinate (u, v) → (x_cm, y_cm) at a specific height h 
        ABOVE the tag plane (where h is in cm).
        
        This uses the estimated 3D camera pose and ray-plane intersection.
        If pose is not available, falls back to standard homography (h=0).
        """
        if not self.scale_calibrated:
            return 0.0, 0.0

        # Fallback to standard homography if we don't have pose info
        if self.rvec is None or self.tvec is None or self.camera_matrix is None:
            return self.pixel_point_to_cm(u, v)

        try:
            R, _ = cv2.Rodrigues(self.rvec)
            # Camera center in Tag Frame: C = -R^T * t
            C_tag = -R.T @ self.tvec
            
            # Pixel Ray in Camera Frame
            K_inv = np.linalg.inv(self.camera_matrix)
            r_cam = K_inv @ np.array([u, v, 1.0], dtype=np.float32)
            
            # Ray direction in Tag Frame
            r_tag = R.T @ r_cam
            
            # Point on ray: P = C_tag + alpha * r_tag
            # Condition: P_z = -h (Assuming Z points INTO the table, so UP is negative Z)
            # Solve for alpha: C_tag_z + alpha * r_tag_z = -h
            # alpha = (-h - C_tag_z) / r_tag_z
            h_target = -h
            denom = r_tag[2]
            if abs(denom) < 1e-6:
                return self.pixel_point_to_cm(u, v) # Fallback if ray parallel to plane
                
            alpha = (h_target - C_tag[2][0]) / denom
            P_tag = C_tag.flatten() + alpha * r_tag
            
            return float(P_tag[0]), float(P_tag[1])
        except Exception as e:
            print(f"Error in projective correction: {e}")
            return self.pixel_point_to_cm(u, v)

    def pixel_distance_to_cm(
        self,
        u1: float, v1: float,
        u2: float, v2: float,
        h: float = 0.0
    ) -> float:
        """
        Euclidean distance in cm between two pixel points, optionally corrected for height h.

        Parameters
        ----------
        u1, v1 : pixel coordinates of point 1
        u2, v2 : pixel coordinates of point 2
        h : Height above tag plane (cm)
        """
        if not self.scale_calibrated:
            return 0.0

        if h == 0:
            x1, y1 = self.pixel_point_to_cm(u1, v1)
            x2, y2 = self.pixel_point_to_cm(u2, v2)
        else:
            x1, y1 = self.pixel_point_to_cm_at_height(u1, v1, h)
            x2, y2 = self.pixel_point_to_cm_at_height(u2, v2, h)
            
        return float(np.hypot(x2 - x1, y2 - y1))

    def get_scale_info(self) -> Dict:
        """Get calibration information for display / export."""
        return {
            'calibrated': self.scale_calibrated,
            'homography_available': self.homography is not None,
            'pose_available': self.rvec is not None,
            'camera_distance_cm': self.camera_distance_cm,
            'pixels_per_cm': self.pixels_per_cm,
            'apriltag_size_cm': self.apriltag_size_cm,
            'apriltag_size_m': self.apriltag_size_m,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _estimate_pose(self, corners: np.ndarray, w: int, h: int):
        """Estimate 3D camera pose relative to AprilTag using a synthetic camera matrix."""
        try:
            # 1. Create Synthetic Camera Matrix (Assume 60 deg HFOV)
            # f = (w / 2) / tan(30deg)
            hfov_rad = np.radians(60.0)
            f = (w / 2.0) / np.tan(hfov_rad / 2.0)
            cx, cy = w / 2.0, h / 2.0
            
            self.camera_matrix = np.array([
                [f, 0, cx],
                [0, f, cy],
                [0, 0, 1]
            ], dtype=np.float32)

            # 2. Define object points (TL, TR, BR, BL) in Tag Frame (Z=0)
            # Following OpenCV ArUco order: TL, TR, BR, BL
            s = self.apriltag_size_cm
            obj_points = np.array([
                [0, 0, 0],
                [s, 0, 0],
                [s, s, 0],
                [0, s, 0]
            ], dtype=np.float32)

            # 3. Solve PnP
            # We use SOLVEPNP_IPPE_SQUARE as it is optimized for planar marker squares
            success, rvec, tvec = cv2.solvePnP(
                obj_points, corners, self.camera_matrix, self.dist_coeffs,
                flags=cv2.SOLVEPNP_IPPE_SQUARE
            )
            
            if success:
                self.rvec = rvec
                self.tvec = tvec
                # Distance is the magnitude of the translation vector
                self.camera_distance_cm = float(np.linalg.norm(tvec))
        except Exception as e:
            print(f"Pose estimation error: {e}")

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
