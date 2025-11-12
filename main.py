import sys
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import cv2
import numpy as np
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QComboBox, QGroupBox, QScrollArea,
    QFileDialog, QMessageBox, QFrame, QTabWidget
)
from PySide6.QtGui import QImage, QPixmap, QColor, QFont, QPainter, QPen, QBrush
from PySide6.QtCore import Qt, QPoint, QSize, Signal

from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from PIL import Image as PILImage


class MeasurementCalculator:
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


class ReportGenerator:
    """Generate comprehensive PDF reports with measurements."""

    def __init__(self):
        self.reports_dir = Path.home() / "Documents" / "HandMetrics" / "reports"
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def generate_report(self, image_path: str, annotated_image: np.ndarray, measurements: Dict, scale_info: Dict) -> str:
        """
        Generate a comprehensive A4 PDF report.

        Args:
            image_path: Path to the source image
            annotated_image: Annotated numpy array with landmarks drawn
            measurements: Dictionary of measurements between joints
            scale_info: Scale calibration information

        Returns:
            Path to generated PDF file
        """
        try:
            # Prepare report filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            image_name = Path(image_path).stem
            report_filename = f"HandMetrics_{image_name}_{timestamp}.pdf"
            report_path = self.reports_dir / report_filename

            # Create PDF document
            doc = SimpleDocTemplate(
                str(report_path),
                pagesize=A4,
                rightMargin=0.5*inch,
                leftMargin=0.5*inch,
                topMargin=0.5*inch,
                bottomMargin=0.5*inch
            )

            # Container for PDF elements
            elements = []
            styles = getSampleStyleSheet()

            # Custom styles
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=18,
                textColor=colors.HexColor('#1a5490'),
                spaceAfter=6,
                alignment=TA_CENTER,
                fontName='Helvetica-Bold'
            )

            heading_style = ParagraphStyle(
                'CustomHeading',
                parent=styles['Heading2'],
                fontSize=11,
                textColor=colors.HexColor('#2e5c8a'),
                spaceAfter=4,
                spaceBefore=4,
                fontName='Helvetica-Bold'
            )

            normal_style = ParagraphStyle(
                'CustomNormal',
                parent=styles['Normal'],
                fontSize=9,
                spaceAfter=2
            )

            # Title
            elements.append(Paragraph("HandMetrics Report", title_style))
            elements.append(Spacer(1, 0.1*inch))

            # Header information
            header_data = [
                [
                    Paragraph(f"<b>Image:</b> {Path(image_path).name}", normal_style),
                    Paragraph(f"<b>Date & Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", normal_style)
                ],
                [
                    Paragraph(f"<b>Scale:</b> {scale_info.get('pixels_per_cm', 'N/A'):.4f} pixels/cm", normal_style),
                    Paragraph(f"<b>AprilTag Size:</b> {scale_info.get('apriltag_size_cm', 'N/A')} cm", normal_style)
                ]
            ]

            header_table = Table(header_data, colWidths=[3.25*inch, 3.25*inch])
            header_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ]))
            elements.append(header_table)
            elements.append(Spacer(1, 0.15*inch))

            # Add annotated image
            try:
                # Convert BGR to RGB (cv2 uses BGR)
                rgb_image = cv2.cvtColor(annotated_image, cv2.COLOR_BGR2RGB)

                # Convert numpy array to PIL Image
                img = PILImage.fromarray(rgb_image)

                # Scale image to fit A4 width while maintaining aspect ratio
                max_width = 6.5 * inch
                max_height = 3.5 * inch
                img.thumbnail((int(max_width), int(max_height)), PILImage.Resampling.LANCZOS)

                img_path_temp = self.reports_dir / f"temp_img_{int(datetime.now().timestamp() * 1000)}.png"
                img.save(str(img_path_temp))

                report_img = Image(str(img_path_temp), width=img.width, height=img.height)
                img_table = Table([[report_img]], colWidths=[6.5*inch])
                img_table.setStyle(TableStyle([
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('LEFTPADDING', (0, 0), (-1, -1), 0),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                ]))
                elements.append(img_table)
                elements.append(Spacer(1, 0.15*inch))
            except Exception as e:
                print(f"Warning: Could not process annotated image: {e}")
                elements.append(Paragraph(f"<i>Annotated image could not be loaded: {e}</i>", normal_style))
                elements.append(Spacer(1, 0.1*inch))

            # Measurements section
            elements.append(Paragraph("Joint Distance Measurements", heading_style))

            # Create measurements table
            measurements_data = [['Finger', 'Joint', 'Distance (cm)', 'Distance (px)']]

            finger_labels = {
                'thumb': 'Thumb',
                'index': 'Index',
                'middle': 'Middle',
                'ring': 'Ring',
                'pinky': 'Pinky'
            }

            for finger in ['thumb', 'index', 'middle', 'ring', 'pinky']:
                finger_measurements = measurements.get(finger, [])
                if finger_measurements:
                    for idx, dist_info in enumerate(finger_measurements):
                        if idx == 0:
                            measurements_data.append([
                                finger_labels[finger],
                                f"J{dist_info['from_joint']}-{dist_info['to_joint']}",
                                f"{dist_info['cm_distance']:.2f}",
                                f"{dist_info['pixel_distance']:.1f}"
                            ])
                        else:
                            measurements_data.append([
                                '',
                                f"J{dist_info['from_joint']}-{dist_info['to_joint']}",
                                f"{dist_info['cm_distance']:.2f}",
                                f"{dist_info['pixel_distance']:.1f}"
                            ])

            if len(measurements_data) > 1:
                measurements_table = Table(measurements_data, colWidths=[1.3*inch, 1.2*inch, 1.5*inch, 1.45*inch])
                measurements_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2e5c8a')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 9),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('FONTSIZE', (0, 1), (-1, -1), 8),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f5f5f5')]),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ]))
                elements.append(measurements_table)
            else:
                elements.append(Paragraph("<i>No measurements available</i>", normal_style))

            # Build PDF
            doc.build(elements)

            # Clean up temp image if it exists
            try:
                img_path_temp.unlink()
            except:
                pass

            return str(report_path)

        except Exception as e:
            print(f"Error generating report: {e}")
            raise


class ImageCanvas(QFrame):
    """Custom widget for displaying image and handling mouse clicks."""

    point_added = Signal(tuple)
    apriltag_detected = Signal(list)
    scale_calibrated = Signal(dict)

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

        # Measurement calculator
        self.measurement_calc = MeasurementCalculator()
        self.show_measurements = False

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

            try:
                detector_params = cv2.aruco.DetectorParameters()
                detector_params.adaptiveThreshConstant = 10
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
                        if self.measurement_calc.calibrate_from_apriltag(corner[0]):
                            scale_info = self.measurement_calc.get_scale_info()
                            self.scale_calibrated.emit(scale_info)
                            print(f"✓ Scale calibrated: {scale_info['pixels_per_cm']:.4f} pixels/cm")

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

    def calculate_joint_distances(self) -> Dict[str, List[Dict]]:
        """Calculate distances between consecutive joints for each finger."""
        distances = {}

        for finger, points in self.selected_points.items():
            finger_distances = []

            if len(points) >= 2:
                for i in range(len(points) - 1):
                    p1 = np.array(points[i])
                    p2 = np.array(points[i + 1])

                    pixel_dist = np.linalg.norm(p2 - p1)
                    cm_dist = self.measurement_calc.pixel_distance_to_cm(pixel_dist)

                    distance_info = {
                        'from_joint': i,
                        'to_joint': i + 1,
                        'pixel_distance': round(pixel_dist, 2),
                        'cm_distance': round(cm_dist, 2)
                    }
                    finger_distances.append(distance_info)

            distances[finger] = finger_distances

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

                    # Draw distance text if showing measurements
                    if self.show_measurements and self.measurement_calc.scale_calibrated:
                        p1 = np.array(points[i])
                        p2 = np.array(points[i+1])
                        pixel_dist = np.linalg.norm(p2 - p1)
                        cm_dist = self.measurement_calc.pixel_distance_to_cm(pixel_dist)

                        # Midpoint for text
                        mid_x = int((points[i][0] + points[i+1][0]) / 2)
                        mid_y = int((points[i][1] + points[i+1][1]) / 2)

                        text = f"{cm_dist:.1f}cm"
                        cv2.putText(display_image, text, (mid_x, mid_y - 5),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)

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

                    # Draw distance text if showing measurements
                    if self.show_measurements and self.measurement_calc.scale_calibrated:
                        p1 = np.array(points[i])
                        p2 = np.array(points[i+1])
                        pixel_dist = float(np.linalg.norm(p2 - p1))
                        cm_dist = self.measurement_calc.pixel_distance_to_cm(pixel_dist)

                        # Midpoint for text
                        mid_x = int((points[i][0] + points[i+1][0]) / 2)
                        mid_y = int((points[i][1] + points[i+1][1]) / 2)

                        text = f"{cm_dist:.1f}cm"
                        cv2.putText(display_image, text, (mid_x, mid_y - 5),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)

        return display_image


class HandAnnotationWithMeasurements(QMainWindow):
    """Main GUI for hand joint annotation with measurements."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("HandMetrics - Hand Joint Annotation Tool")
        self.setGeometry(100, 100, 1500, 950)

        # Initialize report generator
        self.report_generator = ReportGenerator()

        # Create central widget and layouts
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # Center - Image canvas (must be created before left panel)
        self.canvas = ImageCanvas()
        self.canvas.point_added.connect(self.on_point_added)
        self.canvas.apriltag_detected.connect(self.on_apriltag_detected)
        self.canvas.scale_calibrated.connect(self.on_scale_calibrated)

        # Left panel - Controls
        left_panel = self.create_left_panel()

        # Right panel - Landmarks and Measurements display
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
        self.finger_combo.setCurrentIndex(-1)  # Start with no selection
        self.finger_combo.currentTextChanged.connect(self.on_finger_selected)
        layout.addWidget(self.finger_combo)

        # Point counter
        layout.addWidget(QLabel("Points Added:"))
        self.point_counter = QLabel("0 / 4")
        self.point_counter.setStyleSheet("font-size: 14px; font-weight: bold; color: blue;")
        layout.addWidget(self.point_counter)

        # Point labels
        layout.addWidget(QLabel("\nPoint Labels:"))
        for i in range(4):
            label_text = ["Start", "Joint 1", "Joint 2", "End"][i]
            layout.addWidget(QLabel(f"Point {i}: {label_text}"))

        # Measurement section
        layout.addSpacing(20)
        layout.addWidget(QLabel("📏 Measurements:"))

        self.scale_status = QLabel("No scale")
        self.scale_status.setStyleSheet("color: gray; font-weight: bold;")
        layout.addWidget(self.scale_status)

        self.scale_value = QLabel("")
        self.scale_value.setStyleSheet("color: blue; font-size: 10px;")
        layout.addWidget(self.scale_value)

        # Toggle measurements display
        self.toggle_measurements = QPushButton("Show Measurements")
        self.toggle_measurements.setCheckable(True)
        self.toggle_measurements.clicked.connect(self.toggle_measurements_display)
        self.toggle_measurements.setStyleSheet("background-color: #cccccc;")
        layout.addWidget(self.toggle_measurements)

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

        # Generate PDF Report
        report_btn = QPushButton("📄 Generate Report (PDF)")
        report_btn.setStyleSheet("background-color: #0066cc; color: white; font-weight: bold;")
        report_btn.clicked.connect(self.generate_pdf_report)
        layout.addWidget(report_btn)

        layout.addStretch()
        group.setLayout(layout)
        return group

    def create_right_panel(self) -> QGroupBox:
        """Create right panel for displaying landmarks and measurements."""
        group = QGroupBox("Data")
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        # Tab widget for switching between landmarks and measurements
        self.tab_widget = QTabWidget()

        # Tab 1: Landmarks
        landmarks_tab = QWidget()
        landmarks_layout = QVBoxLayout(landmarks_tab)
        landmarks_layout.setContentsMargins(5, 5, 5, 5)
        landmarks_layout.setSpacing(5)

        landmarks_layout.addWidget(QLabel("AprilTags Detected:"))
        self.apriltag_label = QLabel("None")
        self.apriltag_label.setWordWrap(True)
        self.apriltag_label.setStyleSheet("background-color: #f0f0f0; padding: 5px; max-height: 50px;")
        landmarks_layout.addWidget(self.apriltag_label)

        landmarks_layout.addWidget(QLabel("Hand Landmarks:"))

        scroll1 = QScrollArea()
        scroll1.setWidgetResizable(True)
        scroll1.setStyleSheet("QScrollArea { border: 1px solid #cccccc; }")
        self.landmarks_widget = QWidget()
        self.landmarks_layout = QVBoxLayout(self.landmarks_widget)
        self.landmarks_layout.setContentsMargins(2, 2, 2, 2)
        self.landmarks_layout.setSpacing(2)
        scroll1.setWidget(self.landmarks_widget)
        landmarks_layout.addWidget(scroll1, 1)  # Give scroll area maximum stretch

        # Tab 2: Measurements
        measurements_tab = QWidget()
        measurements_layout = QVBoxLayout(measurements_tab)
        measurements_layout.setContentsMargins(5, 5, 5, 5)
        measurements_layout.setSpacing(5)

        measurements_layout.addWidget(QLabel("📏 Joint Distances:"))

        scroll2 = QScrollArea()
        scroll2.setWidgetResizable(True)
        scroll2.setStyleSheet("QScrollArea { border: 1px solid #cccccc; }")
        self.measurements_widget = QWidget()
        self.measurements_layout = QVBoxLayout(self.measurements_widget)
        self.measurements_layout.setContentsMargins(2, 2, 2, 2)
        self.measurements_layout.setSpacing(2)
        scroll2.setWidget(self.measurements_widget)
        measurements_layout.addWidget(scroll2, 1)  # Give scroll area maximum stretch

        # Add tabs
        self.tab_widget.addTab(landmarks_tab, "Landmarks")
        self.tab_widget.addTab(measurements_tab, "Measurements")

        layout.addWidget(self.tab_widget, 1)  # Give tab widget maximum stretch
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
                self.update_measurements_display()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load image: {str(e)}")

    def on_finger_selected(self, finger_text: str):
        """Handle finger selection."""
        # Ignore empty selection
        if not finger_text:
            return

        finger_map = {
            "Thumb": "thumb",
            "Index": "index",
            "Middle": "middle",
            "Ring": "ring",
            "Pinky": "pinky"
        }
        finger = finger_map.get(finger_text)
        if finger:
            self.canvas.set_current_finger(finger)
            self.update_point_counter()

    def on_point_added(self, data):
        """Handle point added event."""
        finger, idx, pos = data
        print(f"Added {finger} point {idx}: {pos}")
        self.update_point_counter()
        self.update_landmarks_display()
        self.update_measurements_display()

    def on_apriltag_detected(self, tags):
        """Handle AprilTag detection."""
        if tags:
            tag_text = "\n".join([f"Tag ID: {tag['id']}" for tag in tags])
            self.apriltag_label.setText(tag_text)
        else:
            self.apriltag_label.setText("No AprilTags detected")

    def on_scale_calibrated(self, scale_info):
        """Handle scale calibration."""
        if scale_info['calibrated']:
            self.scale_status.setText("✓ Scale Calibrated")
            self.scale_status.setStyleSheet("color: green; font-weight: bold;")
            self.scale_value.setText(f"{scale_info['pixels_per_cm']:.4f} pixels/cm")
            self.toggle_measurements.setEnabled(True)
        else:
            self.scale_status.setText("No scale")
            self.scale_status.setStyleSheet("color: gray; font-weight: bold;")
            self.toggle_measurements.setEnabled(False)

    def toggle_measurements_display(self):
        """Toggle measurement display on image."""
        self.canvas.show_measurements = self.toggle_measurements.isChecked()
        if self.canvas.show_measurements:
            self.toggle_measurements.setStyleSheet("background-color: #00cc00; color: white;")
        else:
            self.toggle_measurements.setStyleSheet("background-color: #cccccc;")
        self.canvas.update()

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
            item = self.landmarks_layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()

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

    def update_measurements_display(self):
        """Update measurements display."""
        # Clear previous layout
        while self.measurements_layout.count():
            item = self.measurements_layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()

        # Only show if scale is calibrated
        if not self.canvas.measurement_calc.scale_calibrated:
            no_scale_label = QLabel("⚠️ Load image with AprilTag to enable measurements")
            no_scale_label.setStyleSheet("color: orange; font-style: italic; padding: 10px;")
            self.measurements_layout.addWidget(no_scale_label)
            self.measurements_layout.addStretch()
            return

        distances = self.canvas.calculate_joint_distances()

        finger_labels = {
            'thumb': 'Thumb',
            'index': 'Index',
            'middle': 'Middle',
            'ring': 'Ring',
            'pinky': 'Pinky'
        }

        colors = {
            'thumb': '#6666FF',
            'index': '#66FF66',
            'middle': '#FF6666',
            'ring': '#FFFF66',
            'pinky': '#FF66FF'
        }

        has_measurements = False

        for finger in ['thumb', 'index', 'middle', 'ring', 'pinky']:
            finger_distances = distances[finger]

            if finger_distances:
                has_measurements = True

                # Finger header
                header = QLabel(f"{finger_labels[finger].upper()}")
                header.setStyleSheet(f"background-color: {colors[finger]}; color: white; padding: 5px; font-weight: bold;")
                self.measurements_layout.addWidget(header)

                # Distances
                for dist_info in finger_distances:
                    dist_text = (f"  Joint {dist_info['from_joint']} → {dist_info['to_joint']}: "
                                f"{dist_info['cm_distance']:.2f} cm "
                                f"({dist_info['pixel_distance']:.1f} px)")
                    dist_label = QLabel(dist_text)
                    dist_label.setStyleSheet(f"padding: 3px; border-left: 3px solid {colors[finger]}; font-family: monospace;")
                    self.measurements_layout.addWidget(dist_label)

        if not has_measurements:
            empty_label = QLabel("Add finger landmarks to see measurements")
            empty_label.setStyleSheet("color: gray; font-style: italic; padding: 10px;")
            self.measurements_layout.addWidget(empty_label)

        self.measurements_layout.addStretch()

    def undo_point(self):
        """Undo last point."""
        self.canvas.undo_last_point()
        self.update_point_counter()
        self.update_landmarks_display()
        self.update_measurements_display()

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
                self.update_measurements_display()

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
            self.update_measurements_display()

    def save_landmarks(self):
        """Save landmarks to JSON file with measurements."""
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
                formatted_data['apriltags'] = self.canvas.detected_tags

                # Add scale information
                formatted_data['scale_info'] = self.canvas.measurement_calc.get_scale_info()

                # Add measurements
                formatted_data['measurements'] = self.canvas.calculate_joint_distances()

                with open(file_path, 'w') as f:
                    json.dump(formatted_data, f, indent=2)

                QMessageBox.information(self, "Success", f"Landmarks saved to:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save: {str(e)}")

    def generate_pdf_report(self):
        """Generate a comprehensive PDF report with measurements."""
        # Check if image is loaded
        if self.canvas.image is None:
            QMessageBox.warning(self, "Warning", "Please load an image first.")
            return

        # Check if scale is calibrated
        if not self.canvas.measurement_calc.scale_calibrated:
            QMessageBox.warning(self, "Warning", "Please load an image with AprilTag for scale calibration.")
            return

        # Check if landmarks are added
        landmarks = self.canvas.get_landmarks()
        total_points = sum(len(points) for points in landmarks.values())
        if total_points == 0:
            QMessageBox.warning(self, "Warning", "Please add at least one landmark point.")
            return

        try:
            # Get annotated image
            annotated_image = self.canvas.get_annotated_image()
            if annotated_image is None:
                QMessageBox.warning(self, "Warning", "Could not generate annotated image.")
                return

            # Prepare data for report
            measurements = self.canvas.calculate_joint_distances()
            scale_info = self.canvas.measurement_calc.get_scale_info()

            # Generate report
            report_path = self.report_generator.generate_report(
                str(self.canvas.image_path),
                annotated_image,
                measurements,
                scale_info
            )

            # Show success message with path
            QMessageBox.information(
                self, "Report Generated",
                f"PDF report successfully generated!\n\n"
                f"Location: {report_path}\n\n"
                f"Reports are saved in:\n{self.report_generator.reports_dir}"
            )

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate report:\n{str(e)}")


def main():
    app = QApplication(sys.argv)
    gui = HandAnnotationWithMeasurements()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
