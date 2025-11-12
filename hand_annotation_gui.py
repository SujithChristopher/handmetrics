import sys
import json
from pathlib import Path
from typing import Dict, List, Tuple
import cv2
import numpy as np
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QComboBox, QGroupBox, QScrollArea,
    QFileDialog, QMessageBox, QSpinBox, QFrame
)
from PySide6.QtGui import QImage, QPixmap, QColor, QFont, QPainter, QPen, QBrush
from PySide6.QtCore import Qt, QPoint, QSize, Signal, QEvent


class ImageCanvas(QFrame):
    """Custom widget for displaying image and handling mouse clicks."""

    point_added = Signal(tuple)
    apriltag_detected = Signal(list)

    def __init__(self):
        super().__init__()
        self.setStyleSheet("border: 2px solid #cccccc; background-color: white;")
        self.image = None
        self.image_path = None
        self.selected_points: Dict[str, List[Tuple[int, int]]] = {
            'thumb': [],
            'index': [],
            'middle': [],
            'ring': [],
            'pinky': []
        }
        self.current_finger = None
        self.detected_tags = []
        self.point_radius = 6
        self.line_width = 2

    def set_image(self, image_path):
        """Load and display image."""
        self.image_path = image_path
        self.image = cv2.imread(str(image_path))

        if self.image is None:
            raise ValueError(f"Cannot load image: {image_path}")

        # Detect AprilTags
        self.detect_apriltags()
        self.update()

    def detect_apriltags(self):
        """Detect AprilTag markers in the image using OpenCV ArUco."""
        if self.image is None:
            return

        try:
            gray = cv2.cvtColor(self.image, cv2.COLOR_BGR2GRAY)

            # Try using cv2.aruco for AprilTag detection (tag36h11)
            # Note: OpenCV 4.7+ has built-in apriltag support
            try:
                detector_params = cv2.aruco.DetectorParameters()
                detector_params.adaptiveThreshConstant = 10
                detector = cv2.aruco.ArucoDetector(
                    cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_APRILTAG_36h11),
                    detector_params
                )
                corners, ids, rejected = detector.detectMarkers(gray)
            except AttributeError:
                # Fallback for older OpenCV versions
                aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_APRILTAG_36h11)
                parameters = cv2.aruco.DetectorParameters()
                detector = cv2.aruco.ArucoDetector(aruco_dict, parameters)
                corners, ids, rejected = detector.detectMarkers(gray)

            self.detected_tags = []
            if ids is not None:
                for i, corner in enumerate(corners):
                    tag_info = {
                        'id': ids[i][0],
                        'corners': corner[0].astype(int),
                    }
                    self.detected_tags.append(tag_info)

            self.apriltag_detected.emit(self.detected_tags)
        except Exception as e:
            print(f"AprilTag detection error: {e}")

    def set_current_finger(self, finger: str):
        """Set the current finger for annotation."""
        self.current_finger = finger

    def mousePressEvent(self, event):
        """Handle mouse click to add points."""
        if self.image is None or self.current_finger is None:
            QMessageBox.warning(self, "Warning", "Please load an image and select a finger first.")
            return

        # Get click position relative to the image
        canvas_pos = event.position()
        x, y = int(canvas_pos.x()), int(canvas_pos.y())

        # Scale back to original image coordinates
        if hasattr(self, 'display_image'):
            scale_x = self.image.shape[1] / self.display_image.width()
            scale_y = self.image.shape[0] / self.display_image.height()
            x = int(x * scale_x)
            y = int(y * scale_y)

        # Validate click position
        if x < 0 or y < 0 or x >= self.image.shape[1] or y >= self.image.shape[0]:
            return

        # Add point
        self.selected_points[self.current_finger].append((x, y))
        self.point_added.emit((self.current_finger, len(self.selected_points[self.current_finger]) - 1, (x, y)))
        self.update()

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
            corners = tag['corners']
            cv2.polylines(display_image, [corners], True, (0, 255, 0), 2)
            center = corners.mean(axis=0).astype(int)
            cv2.putText(display_image, f"ID: {tag['id']}", tuple(center),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        # Draw all selected points
        colors = {
            'thumb': (255, 0, 0),      # Blue
            'index': (0, 255, 0),      # Green
            'middle': (0, 0, 255),     # Red
            'ring': (255, 255, 0),     # Cyan
            'pinky': (255, 0, 255)     # Magenta
        }

        for finger, points in self.selected_points.items():
            color = colors[finger]
            for idx, (x, y) in enumerate(points):
                cv2.circle(display_image, (x, y), self.point_radius, color, -1)
                cv2.putText(display_image, f"{idx}", (x + 10, y - 10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

            # Draw skeleton connections if enough points
            if len(points) > 1:
                for i in range(len(points) - 1):
                    cv2.line(display_image, points[i], points[i+1], color, 2)

        # Convert to QPixmap
        rgb_image = cv2.cvtColor(display_image, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)

        # Scale to fit widget
        scaled_pixmap = QPixmap.fromImage(qt_image).scaledToWidth(self.width() - 4, Qt.SmoothTransformation)
        self.display_image = scaled_pixmap

        painter = QPainter(self)
        painter.drawPixmap(2, 2, scaled_pixmap)

    def undo_last_point(self):
        """Remove the last added point."""
        if self.current_finger and self.selected_points[self.current_finger]:
            self.selected_points[self.current_finger].pop()
            self.update()

    def clear_finger(self):
        """Clear all points for current finger."""
        if self.current_finger:
            self.selected_points[self.current_finger] = []
            self.update()

    def clear_all(self):
        """Clear all points for all fingers."""
        for finger in self.selected_points:
            self.selected_points[finger] = []
        self.update()

    def get_landmarks(self) -> Dict:
        """Get all landmarks data."""
        return self.selected_points.copy()

    def resizeEvent(self, event):
        """Handle widget resize."""
        super().resizeEvent(event)
        self.update()


class HandAnnotationGUI(QMainWindow):
    """Main GUI for hand joint annotation."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Hand Joint Annotation Tool")
        self.setGeometry(100, 100, 1400, 900)

        # Create central widget and layouts
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # Left panel - Controls
        left_panel = self.create_left_panel()

        # Center - Image canvas
        self.canvas = ImageCanvas()
        self.canvas.point_added.connect(self.on_point_added)
        self.canvas.apriltag_detected.connect(self.on_apriltag_detected)

        # Right panel - Landmarks display
        right_panel = self.create_right_panel()

        main_layout.addWidget(left_panel, 1)
        main_layout.addWidget(self.canvas, 3)
        main_layout.addWidget(right_panel, 1)

        self.show()

    def create_left_panel(self) -> QGroupBox:
        """Create left control panel."""
        group = QGroupBox("Controls")
        layout = QVBoxLayout()

        # Load Image
        load_btn = QPushButton("Load Image")
        load_btn.clicked.connect(self.load_image)
        layout.addWidget(load_btn)

        # Finger Selection
        layout.addWidget(QLabel("Select Finger:"))
        self.finger_combo = QComboBox()
        self.finger_combo.addItems(["Thumb", "Index", "Middle", "Ring", "Pinky"])
        self.finger_combo.currentTextChanged.connect(self.on_finger_selected)
        layout.addWidget(self.finger_combo)

        # Point counter
        layout.addWidget(QLabel("Points Added:"))
        self.point_counter = QLabel("0 / 4")
        self.point_counter.setStyleSheet("font-size: 14px; font-weight: bold; color: blue;")
        layout.addWidget(self.point_counter)

        # Point labels
        layout.addWidget(QLabel("\nPoint Labels:"))
        self.point_labels = {
            'thumb': [],
            'index': [],
            'middle': [],
            'ring': [],
            'pinky': []
        }
        for i in range(4):
            label_text = ["Start", "Joint 1", "Joint 2", "End"][i]
            layout.addWidget(QLabel(f"Point {i}: {label_text}"))

        # Action buttons
        layout.addSpacing(20)

        undo_btn = QPushButton("Undo Last Point")
        undo_btn.setStyleSheet("background-color: #ffaa00;")
        undo_btn.clicked.connect(self.undo_point)
        layout.addWidget(undo_btn)

        clear_finger_btn = QPushButton("Clear Current Finger")
        clear_finger_btn.setStyleSheet("background-color: #ff6600;")
        clear_finger_btn.clicked.connect(self.clear_current_finger)
        layout.addWidget(clear_finger_btn)

        clear_all_btn = QPushButton("Clear All")
        clear_all_btn.setStyleSheet("background-color: #ff0000; color: white;")
        clear_all_btn.clicked.connect(self.clear_all)
        layout.addWidget(clear_all_btn)

        layout.addSpacing(20)

        # Save annotations
        save_btn = QPushButton("Save Landmarks")
        save_btn.setStyleSheet("background-color: #00cc00; color: white; font-weight: bold;")
        save_btn.clicked.connect(self.save_landmarks)
        layout.addWidget(save_btn)

        layout.addStretch()
        group.setLayout(layout)
        return group

    def create_right_panel(self) -> QGroupBox:
        """Create right panel for displaying landmarks."""
        group = QGroupBox("Landmarks")
        layout = QVBoxLayout()

        # AprilTag info
        layout.addWidget(QLabel("AprilTags Detected:"))
        self.apriltag_label = QLabel("None")
        self.apriltag_label.setWordWrap(True)
        self.apriltag_label.setStyleSheet("background-color: #f0f0f0; padding: 5px;")
        layout.addWidget(self.apriltag_label)

        layout.addSpacing(15)

        # Landmarks display
        layout.addWidget(QLabel("Hand Landmarks:"))

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.landmarks_widget = QWidget()
        self.landmarks_layout = QVBoxLayout(self.landmarks_widget)
        scroll.setWidget(self.landmarks_widget)
        layout.addWidget(scroll)

        layout.addStretch()
        group.setLayout(layout)
        return group

    def load_image(self):
        """Load image from file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Image", "images",
            "Image Files (*.jpg *.jpeg *.png *.bmp)"
        )
        if file_path:
            try:
                self.canvas.set_image(file_path)
                self.canvas.clear_all()
                self.update_landmarks_display()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load image: {str(e)}")

    def on_finger_selected(self, finger_text: str):
        """Handle finger selection."""
        finger_map = {
            "Thumb": "thumb",
            "Index": "index",
            "Middle": "middle",
            "Ring": "ring",
            "Pinky": "pinky"
        }
        finger = finger_map[finger_text]
        self.canvas.set_current_finger(finger)
        self.update_point_counter()

    def on_point_added(self, data):
        """Handle point added event."""
        finger, idx, pos = data
        print(f"Added {finger} point {idx}: {pos}")
        self.update_point_counter()
        self.update_landmarks_display()

    def on_apriltag_detected(self, tags):
        """Handle AprilTag detection."""
        if tags:
            tag_text = "\n".join([f"Tag ID: {tag['id']}" for tag in tags])
            self.apriltag_label.setText(tag_text)
        else:
            self.apriltag_label.setText("No AprilTags detected")

    def update_point_counter(self):
        """Update the point counter display."""
        if self.canvas.current_finger:
            count = len(self.canvas.selected_points[self.canvas.current_finger])
            self.point_counter.setText(f"{count} / 4")

            # Color change based on progress
            if count == 0:
                color = "gray"
            elif count < 4:
                color = "orange"
            else:
                color = "green"
            self.point_counter.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {color};")

    def update_landmarks_display(self):
        """Update the landmarks display in right panel."""
        # Clear previous layout
        while self.landmarks_layout.count():
            self.landmarks_layout.takeAt(0).widget().deleteLater()

        landmarks = self.canvas.get_landmarks()
        finger_labels = {
            'thumb': 'Thumb',
            'index': 'Index',
            'middle': 'Middle',
            'ring': 'Ring',
            'pinky': 'Pinky'
        }
        point_names = ['Start', 'Joint 1', 'Joint 2', 'End']

        colors = {
            'thumb': '#6666FF',      # Blue
            'index': '#66FF66',      # Green
            'middle': '#FF6666',     # Red
            'ring': '#FFFF66',       # Yellow
            'pinky': '#FF66FF'       # Magenta
        }

        for finger in ['thumb', 'index', 'middle', 'ring', 'pinky']:
            points = landmarks[finger]

            # Finger header
            header = QLabel(f"{finger_labels[finger].upper()} ({len(points)}/4)")
            header.setStyleSheet(f"background-color: {colors[finger]}; color: white; padding: 5px; font-weight: bold;")
            self.landmarks_layout.addWidget(header)

            # Points
            for idx, (x, y) in enumerate(points):
                point_label = QLabel(f"  {point_names[idx]}: ({x}, {y})")
                point_label.setStyleSheet(f"padding: 3px; border-left: 3px solid {colors[finger]};")
                self.landmarks_layout.addWidget(point_label)

        self.landmarks_layout.addStretch()

    def undo_point(self):
        """Undo last point."""
        self.canvas.undo_last_point()
        self.update_point_counter()
        self.update_landmarks_display()

    def clear_current_finger(self):
        """Clear points for current finger."""
        if self.canvas.current_finger:
            reply = QMessageBox.question(
                self, "Confirm",
                f"Clear all points for {self.canvas.current_finger}?"
            )
            if reply == QMessageBox.Yes:
                self.canvas.clear_finger()
                self.update_point_counter()
                self.update_landmarks_display()

    def clear_all(self):
        """Clear all points."""
        reply = QMessageBox.question(
            self, "Confirm",
            "Clear all landmarks for all fingers?"
        )
        if reply == QMessageBox.Yes:
            self.canvas.clear_all()
            self.update_point_counter()
            self.update_landmarks_display()

    def save_landmarks(self):
        """Save landmarks to JSON file."""
        landmarks = self.canvas.get_landmarks()

        # Check if all fingers have 4 points
        incomplete = [f for f, p in landmarks.items() if len(p) != 4]

        if incomplete:
            reply = QMessageBox.warning(
                self, "Incomplete Data",
                f"Incomplete fingers: {', '.join(incomplete)}\n\nSave anyway?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return

        # Save dialog
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Landmarks", "hand_landmarks",
            "JSON Files (*.json)"
        )

        if file_path:
            try:
                # Format: finger_joint_index
                formatted_data = {}
                for finger, points in landmarks.items():
                    for idx, (x, y) in enumerate(points):
                        key = f"{finger}_{idx}"
                        formatted_data[key] = {"x": x, "y": y}

                # Add image path
                formatted_data['image_path'] = str(self.canvas.image_path)

                # Add detected AprilTags
                formatted_data['apriltags'] = [
                    {'id': tag['id'], 'corners': tag['corners'].tolist()}
                    for tag in self.canvas.detected_tags
                ]

                with open(file_path, 'w') as f:
                    json.dump(formatted_data, f, indent=2)

                QMessageBox.information(self, "Success", f"Landmarks saved to:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save: {str(e)}")


def main():
    app = QApplication(sys.argv)
    gui = HandAnnotationGUI()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
