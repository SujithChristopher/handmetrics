import cv2
import numpy as np
from typing import Dict, List, Tuple, Optional
import pillow_heif
from PIL import Image
from PySide6.QtWidgets import QFrame, QMessageBox
from PySide6.QtGui import QImage, QPixmap, QPainter
from PySide6.QtCore import Qt, Signal, QRect

from core.measurement import MeasurementCalculator
from core.hand_detector import HandDetector

class ImageCanvas(QFrame):
    """
    Custom Widget: Manages the interactive image area.
    Handles:
    - AprilTag detection using OpenCV
    - Landmark point management (adding, removing, clearing)
    - Real-time drawing of annotations and measurement overlays
    """
    """Custom widget for displaying image and handling mouse clicks."""

    point_added = Signal(tuple)
    apriltag_detected = Signal(list)
    scale_calibrated = Signal(dict)
    hand_detected = Signal(str)

    def __init__(self):
        super().__init__()
        self.setStyleSheet("border: 2px solid #cccccc; background-color: white;")
        self.image = None
        self.image_path = None
        self.selected_points: Dict[str, List[Tuple[int, int]]] = {
            'crease1': [],
            'crease2': [],
            'crease3': []
        }
        self.current_crease = None
        self.detected_tags = []
        self.point_radius = 6
        self.line_width = 2

        # Measurement calculator
        self.measurement_calc = MeasurementCalculator()
        self.hand_detector = HandDetector()
        self.detected_hand = "Unknown"
        self.mp_landmarks = []
        self.show_mediapipe_plots = False
        self.show_measurements = False
        self.enable_height_correction = False  # New: Perspective correction for elevated hand
        
        # Display state
        self.image_rect = QRect()  # The actual rectangle where the image is drawn
        self.scale_factor = 1.0    # Current scale factor (pixels to display units)
        
        # Zoom and Pan state
        self.zoom_factor = 1.0
        self.pan_x = 0.0
        self.pan_y = 0.0
        self.is_panning = False
        self.last_pan_pos = None

    def set_image(self, image_path):
        """Load and display image."""
        self.image_path = image_path
        path_str = str(image_path)
        
        if path_str.lower().endswith(('.heic', '.heif')):
            try:
                heif_file = pillow_heif.read_heif(path_str)
                image = Image.frombytes(
                    heif_file.mode,
                    heif_file.size,
                    heif_file.data,
                    "raw",
                )
                # Convert PIL image to BGR numpy array for OpenCV
                self.image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            except Exception as e:
                print(f"Error loading HEIC image: {e}")
                self.image = None
        else:
            self.image = cv2.imread(path_str)

        if self.image is None:
            raise ValueError(f"Cannot load image: {image_path}")
            
        # Detect Hand Side (Send RGB image to detector)
        rgb_image = cv2.cvtColor(self.image, cv2.COLOR_BGR2RGB)
        self.detected_hand, self.mp_landmarks = self.hand_detector.detect_hand_side(rgb_image)
        self.hand_detected.emit(self.detected_hand)

        # Detect AprilTags
        self.detect_apriltags()
        self.update()

    def detect_apriltags(self):
        """Detect AprilTag markers in the image using OpenCV ArUco."""
        if self.image is None:
            return

        try:
            gray = cv2.cvtColor(self.image, cv2.COLOR_BGR2GRAY)

            try:
                detector_params = cv2.aruco.DetectorParameters()
                # detector_params.adaptiveThreshConstant = 10
                detector = cv2.aruco.ArucoDetector(
                    cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_APRILTAG_36h11),
                    detector_params
                )
                corners, ids, rejected = detector.detectMarkers(gray)
            except AttributeError:
                aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_APRILTAG_36h11)
                parameters = cv2.aruco.DetectorParameters()
                detector = cv2.aruco.ArucoDetector(aruco_dict, parameters)
                corners, ids, rejected = detector.detectMarkers(gray)

            self.detected_tags = []
            if ids is not None:
                for i, corner in enumerate(corners):
                    tag_info = {
                        'id': ids[i][0],
                        'corners': corner[0].astype(int).tolist(),
                    }
                    self.detected_tags.append(tag_info)

                    # Calibrate measurement using first detected tag
                    if i == 0:
                        h, w = self.image.shape[:2]
                        if self.measurement_calc.calibrate_from_apriltag(corner[0], img_w=w, img_h=h):
                            scale_info = self.measurement_calc.get_scale_info()
                            self.scale_calibrated.emit(scale_info)
                            print(f"✓ Homography calibrated from AprilTag (approx {scale_info['pixels_per_cm']:.2f} px/cm)")
                            if scale_info.get('pose_available'):
                                print(f"✓ Pose estimated: distance ~{scale_info['camera_distance_cm']:.1f} cm")

            self.apriltag_detected.emit(self.detected_tags)
        except Exception as e:
            print(f"AprilTag detection error: {e}")

    def rotate_image(self, clockwise: bool = True):
        """Rotate image by 90 degrees (+90 if clockwise, -90 if counter-clockwise)."""
        if self.image is None:
            return

        h, w = self.image.shape[:2]

        # Rotate the numpy array
        if clockwise:
            self.image = cv2.rotate(self.image, cv2.ROTATE_90_CLOCKWISE)
            # Math: (x, y) -> (H - 1 - y, x)
            for crease, points in self.selected_points.items():
                new_points = []
                for x, y in points:
                    new_points.append((h - 1 - y, x))
                self.selected_points[crease] = new_points
        else:
            self.image = cv2.rotate(self.image, cv2.ROTATE_90_COUNTERCLOCKWISE)
            # Math: (x, y) -> (y, W - 1 - x)
            for crease, points in self.selected_points.items():
                new_points = []
                for x, y in points:
                    new_points.append((y, w - 1 - x))
                self.selected_points[crease] = new_points

        # Re-detect AprilTags because their coordinate spaces have changed
        self.detect_apriltags()

        # Reset zoom/pan so they don't get disorienting
        self.zoom_factor = 1.0
        self.pan_x = 0.0
        self.pan_y = 0.0

        self.update()

    def set_current_crease(self, crease: str):
        """Set the current crease for annotation."""
        self.current_crease = crease

    def wheelEvent(self, event):
        """Handle mouse wheel for zooming."""
        if event.modifiers() & Qt.ControlModifier:
            old_zoom = self.zoom_factor
            
            delta = event.angleDelta().y()
            if delta > 0:
                self.zoom_factor *= 1.1
            elif delta < 0:
                self.zoom_factor /= 1.1
                
            self.zoom_factor = max(1.0, min(50.0, self.zoom_factor))
            
            if self.zoom_factor == 1.0:
                self.pan_x = 0.0
                self.pan_y = 0.0
            elif self.image is not None and old_zoom != self.zoom_factor and not self.image_rect.isEmpty():
                # Zoom-to-cursor logic
                mouse_pos = event.position()
                mouse_x = mouse_pos.x()
                mouse_y = mouse_pos.y()
                
                # Image coordinates corresponding to the mouse
                img_x = (mouse_x - self.image_rect.x()) / self.scale_factor
                img_y = (mouse_y - self.image_rect.y()) / self.scale_factor
                
                widget_w = self.width() - 4
                widget_h = self.height() - 4
                h, w = self.image.shape[:2]
                
                base_scale = min(widget_w / w, widget_h / h)
                new_scale = base_scale * self.zoom_factor
                
                target_w = w * new_scale
                target_h = h * new_scale
                
                self.pan_x = mouse_x - img_x * new_scale - (widget_w - target_w) / 2.0 - 2.0
                self.pan_y = mouse_y - img_y * new_scale - (widget_h - target_h) / 2.0 - 2.0
                
            self.update()
            event.accept()
        else:
            super().wheelEvent(event)

    def mousePressEvent(self, event):
        """Handle mouse click to add points or start panning."""
        if event.button() in (Qt.RightButton, Qt.MiddleButton):
            self.is_panning = True
            self.last_pan_pos = event.position()
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
            return

        if self.image is None or self.current_crease is None:
            QMessageBox.warning(self, "Warning", "Please load an image and select a crease first.")
            return

        # Get click position relative to the widget
        canvas_pos = event.position()
        click_x, click_y = canvas_pos.x(), canvas_pos.y()

        # Check if click is inside the image rectangle
        if not self.image_rect.contains(int(click_x), int(click_y)):
            return

        # Map click coordinates to original image coordinates
        # 1. Translate to image origin
        rel_x = click_x - self.image_rect.x()
        rel_y = click_y - self.image_rect.y()
        
        # 2. Scale back to original resolution
        # scale_factor = displayed_size / original_size
        # original_pos = rel_pos / scale_factor
        x = int(rel_x / self.scale_factor)
        y = int(rel_y / self.scale_factor)

        # Validate click position
        if x < 0 or y < 0 or x >= self.image.shape[1] or y >= self.image.shape[0]:
            return

        # Add point
        self.selected_points[self.current_crease].append((x, y))
        self.point_added.emit((self.current_crease, len(self.selected_points[self.current_crease]) - 1, (x, y)))
        self.update()

    def mouseMoveEvent(self, event):
        """Handle mouse drag for panning."""
        if self.is_panning and self.last_pan_pos is not None:
            delta = event.position() - self.last_pan_pos
            self.pan_x += delta.x()
            self.pan_y += delta.y()
            self.last_pan_pos = event.position()
            self.update()
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """Handle end of panning."""
        if self.is_panning:
            if event.button() in (Qt.RightButton, Qt.MiddleButton):
                self.is_panning = False
                self.last_pan_pos = None
                self.unsetCursor()
                event.accept()
                return
        super().mouseReleaseEvent(event)

    def calculate_joint_distances(self) -> Dict[str, List[Dict]]:
        """Calculate distances only for pairs (p0-p1, p2-p3, p4-p5, etc.).
        Skips gaps between segments (p1-p2, p3-p4, etc.)."""
        distances = {}

        for crease, points in self.selected_points.items():
            crease_distances = []

            if len(points) >= 2:
                # Only measure pairs: (0,1), (2,3), (4,5), etc.
                for i in range(0, len(points) - 1, 2):
                    if i + 1 < len(points):  # Make sure we have a pair
                        p1 = np.array(points[i])
                        p2 = np.array(points[i + 1])

                        # Initial raw distance calculation (used for height estimate)
                        pixel_dist = float(np.linalg.norm(p2 - p1))
                        raw_cm_dist = self.measurement_calc.pixel_distance_to_cm(
                            float(p1[0]), float(p1[1]),
                            float(p2[0]), float(p2[1]),
                            h=0.0
                        )

                        current_h = (raw_cm_dist / 2.0) if self.enable_height_correction else 0.0
                        
                        cm_dist = self.measurement_calc.pixel_distance_to_cm(
                            float(p1[0]), float(p1[1]),
                            float(p2[0]), float(p2[1]),
                            h=current_h
                        )

                        distance_info = {
                            'from_point': i,
                            'to_point': i + 1,
                            'pixel_distance': round(pixel_dist, 2),
                            'cm_distance': round(cm_dist, 2)
                        }
                        crease_distances.append(distance_info)

            distances[crease] = crease_distances

        return distances

    def paintEvent(self, event):
        """Custom paint to display image with detected points and AprilTags."""
        if self.image is None:
            return

        # Convert image to QPixmap
        h, w = self.image.shape[:2]

        # Create display image with annotations
        display_image = self.image.copy()

        # Draw AprilTags
        for tag in self.detected_tags:
            corners = np.array(tag['corners'], dtype=np.int32)
            cv2.polylines(display_image, [corners], True, (0, 255, 0), 2)
            center = corners.mean(axis=0).astype(int)
            cv2.putText(display_image, f"ID: {tag['id']}", tuple(center),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        # Draw all selected points
        colors = {
            'crease1': (255, 0, 0),      # Blue
            'crease2': (0, 255, 0),      # Green
            'crease3': (0, 0, 255)       # Red
        }

        for crease, points in self.selected_points.items():
            color = colors[crease]
            for idx, (x, y) in enumerate(points):
                cv2.circle(display_image, (x, y), self.point_radius, color, -1)
                cv2.putText(display_image, f"{idx}", (x + 10, y - 10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

            # Draw skeleton connections only for pairs (p0-p1, p2-p3, p4-p5, etc.)
            # Skip gaps between pairs (p1-p2, p3-p4, etc.)
            if len(points) > 1:
                for i in range(0, len(points) - 1, 2):  # Only even indices (0, 2, 4, ...)
                    if i + 1 < len(points):  # Make sure we have a pair
                        cv2.line(display_image, points[i], points[i+1], color, 2)

                        # Draw distance text if showing measurements
                        if self.show_measurements and self.measurement_calc.scale_calibrated:
                            p1 = np.array(points[i])
                            p2 = np.array(points[i+1])
                            pixel_dist = float(np.linalg.norm(p2 - p1))
                            raw_cm_dist = self.measurement_calc.pixel_distance_to_cm(
                                float(p1[0]), float(p1[1]),
                                float(p2[0]), float(p2[1]),
                                h=0.0
                            )
                            current_h = (raw_cm_dist / 2.0) if self.enable_height_correction else 0.0
                            cm_dist = self.measurement_calc.pixel_distance_to_cm(
                                float(p1[0]), float(p1[1]),
                                float(p2[0]), float(p2[1]),
                                h=current_h
                            )

                            # Midpoint for text
                            mid_x = int((points[i][0] + points[i+1][0]) / 2)
                            mid_y = int((points[i][1] + points[i+1][1]) / 2)

                            text = f"{cm_dist:.1f}cm"
                            cv2.putText(display_image, text, (mid_x, mid_y - 5),
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)

        # Draw MediaPipe hand landmarks if toggled
        if self.show_mediapipe_plots and self.mp_landmarks:
            h, w = display_image.shape[:2]
            mp_connections = [
                (0, 1), (1, 2), (2, 3), (3, 4),  # Thumb
                (0, 5), (5, 6), (6, 7), (7, 8),  # Index
                (5, 9), (9, 10), (10, 11), (11, 12),  # Middle
                (9, 13), (13, 14), (14, 15), (15, 16),  # Ring
                (13, 17), (0, 17), (17, 18), (18, 19), (19, 20)  # Pinky
            ]
            
            points_px = []
            for lm in self.mp_landmarks:
                px, py = int(lm.x * w), int(lm.y * h)
                points_px.append((px, py))
                cv2.circle(display_image, (px, py), 4, (0, 255, 255), -1)  # Yellow dots
            
            for start_idx, end_idx in mp_connections:
                if start_idx < len(points_px) and end_idx < len(points_px):
                    cv2.line(display_image, points_px[start_idx], points_px[end_idx], (0, 165, 255), 2)  # Orange lines

        # Convert to QPixmap
        rgb_image = cv2.cvtColor(display_image, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)

        # Base scale to fit widget
        widget_w = self.width() - 4
        widget_h = self.height() - 4
        
        base_scale = min(widget_w / w, widget_h / h)
        total_scale = base_scale * self.zoom_factor
        
        target_w = int(w * total_scale)
        target_h = int(h * total_scale)
        
        # Calculate centering and pan offsets
        offset_x = int((widget_w - target_w) / 2.0 + 2.0 + self.pan_x)
        offset_y = int((widget_h - target_h) / 2.0 + 2.0 + self.pan_y)
        
        # Store for coordinate mapping
        self.image_rect = QRect(offset_x, offset_y, target_w, target_h)
        self.scale_factor = total_scale
        
        full_pixmap = QPixmap.fromImage(qt_image)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        painter.drawPixmap(self.image_rect, full_pixmap)

    def undo_last_point(self):
        """Remove the last added point."""
        if self.current_crease and self.selected_points[self.current_crease]:
            self.selected_points[self.current_crease].pop()
            self.update()

    def clear_crease(self):
        """Clear all points for current crease."""
        if self.current_crease:
            self.selected_points[self.current_crease] = []
            self.update()

    def clear_all(self):
        """Clear all points for all creases."""
        for crease in self.selected_points:
            self.selected_points[crease] = []
        self.update()

    def get_landmarks(self) -> Dict:
        """Get all landmarks data."""
        return self.selected_points.copy()

    def resizeEvent(self, event):
        """Handle widget resize."""
        super().resizeEvent(event)
        self.update()

    def get_annotated_image(self) -> Optional[np.ndarray]:
        """Get the annotated image as numpy array (full resolution)."""
        if self.image is None:
            return None

        display_image = self.image.copy()

        # Draw AprilTags
        for tag in self.detected_tags:
            corners = np.array(tag['corners'], dtype=np.int32)
            cv2.polylines(display_image, [corners], True, (0, 255, 0), 2)
            center = corners.mean(axis=0).astype(int)
            cv2.putText(display_image, f"ID: {tag['id']}", tuple(center),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        # Draw all selected points
        colors = {
            'crease1': (255, 0, 0),      # Blue
            'crease2': (0, 255, 0),      # Green
            'crease3': (0, 0, 255)       # Red
        }

        for crease, points in self.selected_points.items():
            color = colors[crease]
            for idx, (x, y) in enumerate(points):
                cv2.circle(display_image, (x, y), self.point_radius, color, -1)
                cv2.putText(display_image, f"{idx}", (x + 10, y - 10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

            # Draw skeleton connections only for pairs (p0-p1, p2-p3, p4-p5, etc.)
            # Skip gaps between pairs (p1-p2, p3-p4, etc.)
            if len(points) > 1:
                for i in range(0, len(points) - 1, 2):  # Only even indices (0, 2, 4, ...)
                    if i + 1 < len(points):  # Make sure we have a pair
                        cv2.line(display_image, points[i], points[i+1], color, 2)

                        # Draw distance text if showing measurements
                        if self.show_measurements and self.measurement_calc.scale_calibrated:
                            p1 = np.array(points[i])
                            p2 = np.array(points[i+1])
                            pixel_dist = float(np.linalg.norm(p2 - p1))
                            raw_cm_dist = self.measurement_calc.pixel_distance_to_cm(
                                float(p1[0]), float(p1[1]),
                                float(p2[0]), float(p2[1]),
                                h=0.0
                            )
                            current_h = (raw_cm_dist / 2.0) if self.enable_height_correction else 0.0
                            cm_dist = self.measurement_calc.pixel_distance_to_cm(
                                float(p1[0]), float(p1[1]),
                                float(p2[0]), float(p2[1]),
                                h=current_h
                            )

                            # Midpoint for text
                            mid_x = int((points[i][0] + points[i+1][0]) / 2)
                            mid_y = int((points[i][1] + points[i+1][1]) / 2)

                            text = f"{cm_dist:.1f}cm"
                            cv2.putText(display_image, text, (mid_x, mid_y - 5),
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)

        return display_image
