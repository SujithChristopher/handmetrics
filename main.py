import sys
import json
import csv
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

import matplotlib
matplotlib.use('QtAgg')
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


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
            elements.append(Paragraph("Crease Distance Measurements", heading_style))

            # Create measurements table
            measurements_data = [['Crease', 'Points', 'Distance (cm)', 'Distance (px)']]

            crease_labels = {
                'crease1': 'Crease 1',
                'crease2': 'Crease 2',
                'crease3': 'Crease 3'
            }

            for crease in ['crease1', 'crease2', 'crease3']:
                crease_measurements = measurements.get(crease, [])
                if crease_measurements:
                    for idx, dist_info in enumerate(crease_measurements):
                        if idx == 0:
                            measurements_data.append([
                                crease_labels[crease],
                                f"p{dist_info['from_point']}→p{dist_info['to_point']}",
                                f"{dist_info['cm_distance']:.2f}",
                                f"{dist_info['pixel_distance']:.1f}"
                            ])
                        else:
                            measurements_data.append([
                                '',
                                f"p{dist_info['from_point']}→p{dist_info['to_point']}",
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

    def set_current_crease(self, crease: str):
        """Set the current crease for annotation."""
        self.current_crease = crease

    def mousePressEvent(self, event):
        """Handle mouse click to add points."""
        if self.image is None or self.current_crease is None:
            QMessageBox.warning(self, "Warning", "Please load an image and select a crease first.")
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
        self.selected_points[self.current_crease].append((x, y))
        self.point_added.emit((self.current_crease, len(self.selected_points[self.current_crease]) - 1, (x, y)))
        self.update()

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

                        pixel_dist = float(np.linalg.norm(p2 - p1))
                        cm_dist = self.measurement_calc.pixel_distance_to_cm(pixel_dist)

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

        # Center - Geometric plot canvas
        self.figure = Figure(figsize=(10, 10))
        self.plot_canvas = FigureCanvas(self.figure)
        self.plot_canvas.setStyleSheet("background-color: #1a1a1a; border: 2px solid #333;")

        # Create container for center area (to switch between image and plot)
        self.center_container = QWidget()
        center_layout = QVBoxLayout(self.center_container)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.addWidget(self.canvas)
        center_layout.addWidget(self.plot_canvas)

        # Initially show canvas, hide plot
        self.plot_canvas.hide()
        self.view_mode = "image"  # "image" or "plot"

        # Left panel - Controls
        left_panel = self.create_left_panel()

        # Right panel - Landmarks and Measurements display
        right_panel = self.create_right_panel()

        main_layout.addWidget(left_panel, 1)
        main_layout.addWidget(self.center_container, 3)
        main_layout.addWidget(right_panel, 1)

        self.show()

    def create_left_panel(self) -> QGroupBox:
        """Create left control panel."""
        group = QGroupBox("Controls")
        layout = QVBoxLayout()
        layout.setSpacing(10)

        # Load Image
        load_btn = QPushButton("📂 Load Image")
        load_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; font-size: 11px; padding: 8px; border-radius: 5px;")
        load_btn.setMinimumHeight(40)
        load_btn.clicked.connect(self.load_image)
        layout.addWidget(load_btn)

        # View Mode Toggle
        self.view_toggle_btn = QPushButton("📊 Switch to Plot View")
        self.view_toggle_btn.setStyleSheet("background-color: #9C27B0; color: white; font-weight: bold; font-size: 11px; padding: 8px; border-radius: 5px;")
        self.view_toggle_btn.setMinimumHeight(40)
        self.view_toggle_btn.clicked.connect(self.toggle_view_mode)
        layout.addWidget(self.view_toggle_btn)

        layout.addSpacing(10)

        # Crease Selection
        crease_label = QLabel("Select Crease:")
        crease_label.setStyleSheet("font-size: 11px; font-weight: bold; color: #FFFFFF;")
        layout.addWidget(crease_label)
        self.crease_combo = QComboBox()
        self.crease_combo.addItems(["Crease 1", "Crease 2", "Crease 3"])
        self.crease_combo.setCurrentIndex(-1)  # Start with no selection
        self.crease_combo.setStyleSheet("font-size: 11px; padding: 5px; border-radius: 3px; border: 1px solid #bbb;")
        self.crease_combo.setMinimumHeight(32)
        self.crease_combo.currentTextChanged.connect(self.on_crease_selected)
        layout.addWidget(self.crease_combo)

        # Point counter
        points_label = QLabel("Points in Current Crease:")
        points_label.setStyleSheet("font-size: 11px; font-weight: bold; color: #FFFFFF;")
        layout.addWidget(points_label)
        self.point_counter = QLabel("0 points")
        self.point_counter.setStyleSheet("font-size: 16px; font-weight: bold; color: #2196F3; padding: 8px; background-color: #f0f8ff; border-radius: 3px;")
        layout.addWidget(self.point_counter)

        # Instructions
        instructions = QLabel("Click on the image to add points\nalong the selected crease.\n\nDistances will be measured\nsequentially: p0→p1, p1→p2, etc.")
        instructions.setStyleSheet("font-size: 10px; color: #E0E0E0; font-style: italic; margin-top: 10px; padding: 8px; background-color: rgba(255,255,255,0.05); border-radius: 3px;")
        instructions.setWordWrap(True)
        layout.addWidget(instructions)

        # Measurement section
        layout.addSpacing(15)
        measurements_title = QLabel("📏 Measurements:")
        measurements_title.setStyleSheet("font-size: 12px; font-weight: bold; color: #1a5490;")
        layout.addWidget(measurements_title)

        self.scale_status = QLabel("No scale")
        self.scale_status.setStyleSheet("font-size: 11px; font-weight: bold; color: #FFFFFF; padding: 6px; background-color: #f5f5f5; border-radius: 3px;")
        layout.addWidget(self.scale_status)

        self.scale_value = QLabel("")
        self.scale_value.setStyleSheet("font-size: 10px; color: #2196F3; padding: 4px;")
        layout.addWidget(self.scale_value)

        # Toggle measurements display
        self.toggle_measurements = QPushButton("Show Measurements")
        self.toggle_measurements.setCheckable(True)
        self.toggle_measurements.setStyleSheet("background-color: #d0d0d0; color: #000000; font-weight: bold; font-size: 10px; padding: 6px; border-radius: 3px;")
        self.toggle_measurements.setMinimumHeight(32)
        self.toggle_measurements.clicked.connect(self.toggle_measurements_display)
        layout.addWidget(self.toggle_measurements)

        # Action buttons
        layout.addSpacing(15)

        undo_btn = QPushButton("↶ Undo Last Point")
        undo_btn.setStyleSheet("background-color: #FF9800; color: white; font-weight: bold; font-size: 10px; padding: 6px; border-radius: 3px;")
        undo_btn.setMinimumHeight(32)
        undo_btn.clicked.connect(self.undo_point)
        layout.addWidget(undo_btn)

        clear_crease_btn = QPushButton("🗑️ Clear Current Crease")
        clear_crease_btn.setStyleSheet("background-color: #FF5722; color: white; font-weight: bold; font-size: 10px; padding: 6px; border-radius: 3px;")
        clear_crease_btn.setMinimumHeight(32)
        clear_crease_btn.clicked.connect(self.clear_current_crease)
        layout.addWidget(clear_crease_btn)

        clear_all_btn = QPushButton("⚠️ Clear All")
        clear_all_btn.setStyleSheet("background-color: #F44336; color: white; font-weight: bold; font-size: 10px; padding: 6px; border-radius: 3px;")
        clear_all_btn.setMinimumHeight(32)
        clear_all_btn.clicked.connect(self.clear_all)
        layout.addWidget(clear_all_btn)

        layout.addSpacing(15)

        # Save Landmarks
        save_btn = QPushButton("💾 Save Landmarks (JSON)")
        save_btn.setStyleSheet("background-color: #00cc00; color: white; font-weight: bold; font-size: 11px; padding: 10px; border-radius: 5px;")
        save_btn.setMinimumHeight(44)
        save_btn.clicked.connect(self.save_landmarks)
        layout.addWidget(save_btn)

        # Save Analysis CSV
        save_csv_btn = QPushButton("💾 Save Analysis (CSV)")
        save_csv_btn.setStyleSheet("background-color: #009900; color: white; font-weight: bold; font-size: 11px; padding: 10px; border-radius: 5px;")
        save_csv_btn.setMinimumHeight(44)
        save_csv_btn.clicked.connect(self.save_analysis_csv)
        layout.addWidget(save_csv_btn)

        # Generate PDF Report
        report_btn = QPushButton("📄 Generate Report (PDF)")
        report_btn.setStyleSheet("background-color: #0066cc; color: white; font-weight: bold; font-size: 11px; padding: 10px; border-radius: 5px;")
        report_btn.setMinimumHeight(44)
        report_btn.clicked.connect(self.generate_pdf_report)
        layout.addWidget(report_btn)

        layout.addStretch()
        group.setLayout(layout)
        return group

    def create_right_panel(self) -> QGroupBox:
        """Create right panel for displaying landmarks and measurements."""
        group = QGroupBox("Data")
        group.setStyleSheet("font-size: 11px; font-weight: bold;")
        layout = QVBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Tab widget for switching between landmarks and measurements
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("QTabWidget { font-size: 10px; } QTabBar::tab { padding: 6px 12px; margin: 2px; }")

        # Tab 1: Landmarks
        landmarks_tab = QWidget()
        landmarks_layout = QVBoxLayout(landmarks_tab)
        landmarks_layout.setContentsMargins(8, 8, 8, 8)
        landmarks_layout.setSpacing(8)

        apriltag_title = QLabel("AprilTags Detected:")
        apriltag_title.setStyleSheet("font-size: 11px; font-weight: bold; color: #1a5490;")
        landmarks_layout.addWidget(apriltag_title)
        self.apriltag_label = QLabel("None")
        self.apriltag_label.setWordWrap(True)
        self.apriltag_label.setStyleSheet("background-color: #f0f0f0; padding: 8px; max-height: 50px; border-radius: 3px; font-size: 10px;")
        landmarks_layout.addWidget(self.apriltag_label)

        landmarks_header = QLabel("Hand Landmarks:")
        landmarks_header.setStyleSheet("font-size: 11px; font-weight: bold; color: #1a5490; margin-top: 8px;")
        landmarks_layout.addWidget(landmarks_header)

        scroll1 = QScrollArea()
        scroll1.setWidgetResizable(True)
        scroll1.setStyleSheet("QScrollArea { border: 1px solid #ddd; border-radius: 3px; background-color: white; }")
        self.landmarks_widget = QWidget()
        self.landmarks_layout = QVBoxLayout(self.landmarks_widget)
        self.landmarks_layout.setContentsMargins(4, 4, 4, 4)
        self.landmarks_layout.setSpacing(3)
        scroll1.setWidget(self.landmarks_widget)
        landmarks_layout.addWidget(scroll1, 1)  # Give scroll area maximum stretch

        # Tab 2: Measurements
        measurements_tab = QWidget()
        measurements_layout = QVBoxLayout(measurements_tab)
        measurements_layout.setContentsMargins(8, 8, 8, 8)
        measurements_layout.setSpacing(8)

        measurements_header = QLabel("📏 Joint Distances:")
        measurements_header.setStyleSheet("font-size: 11px; font-weight: bold; color: #1a5490;")
        measurements_layout.addWidget(measurements_header)

        scroll2 = QScrollArea()
        scroll2.setWidgetResizable(True)
        scroll2.setStyleSheet("QScrollArea { border: 1px solid #ddd; border-radius: 3px; background-color: white; }")
        self.measurements_widget = QWidget()
        self.measurements_layout = QVBoxLayout(self.measurements_widget)
        self.measurements_layout.setContentsMargins(4, 4, 4, 4)
        self.measurements_layout.setSpacing(3)
        scroll2.setWidget(self.measurements_widget)
        measurements_layout.addWidget(scroll2, 1)  # Give scroll area maximum stretch

        # Add tabs with improved styling
        self.tab_widget.addTab(landmarks_tab, "📍 Landmarks")
        self.tab_widget.addTab(measurements_tab, "📐 Measurements")

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

    def on_crease_selected(self, crease_text: str):
        """Handle crease selection."""
        # Ignore empty selection
        if not crease_text:
            return

        crease_map = {
            "Crease 1": "crease1",
            "Crease 2": "crease2",
            "Crease 3": "crease3"
        }
        crease = crease_map.get(crease_text)
        if crease:
            self.canvas.set_current_crease(crease)
            self.update_point_counter()

    def on_point_added(self, data):
        """Handle point added event."""
        crease, idx, pos = data
        print(f"Added {crease} point {idx}: {pos}")
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
        if self.canvas.current_crease:
            count = len(self.canvas.selected_points[self.canvas.current_crease])
            point_word = "point" if count == 1 else "points"
            self.point_counter.setText(f"{count} {point_word}")

            # Color change based on count
            if count == 0:
                color = "gray"
            elif count == 1:
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
        crease_labels = {
            'crease1': 'Crease 1',
            'crease2': 'Crease 2',
            'crease3': 'Crease 3'
        }

        colors = {
            'crease1': '#6666FF',      # Blue
            'crease2': '#66FF66',      # Green
            'crease3': '#FF6666'       # Red
        }

        for crease in ['crease1', 'crease2', 'crease3']:
            points = landmarks[crease]

            # Crease header
            header = QLabel(f"{crease_labels[crease].upper()} ({len(points)} points)")
            header.setStyleSheet(f"background-color: {colors[crease]}; color: white; padding: 5px; font-weight: bold;")
            self.landmarks_layout.addWidget(header)

            # Points
            for idx, (x, y) in enumerate(points):
                point_label = QLabel(f"  p{idx}: ({x}, {y})")
                point_label.setStyleSheet(f"padding: 3px; border-left: 3px solid {colors[crease]};")
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

        crease_labels = {
            'crease1': 'Crease 1',
            'crease2': 'Crease 2',
            'crease3': 'Crease 3'
        }

        colors = {
            'crease1': '#6666FF',
            'crease2': '#66FF66',
            'crease3': '#FF6666'
        }

        has_measurements = False

        for crease in ['crease1', 'crease2', 'crease3']:
            crease_distances = distances[crease]

            if crease_distances:
                has_measurements = True

                # Crease header
                header = QLabel(f"{crease_labels[crease].upper()}")
                header.setStyleSheet(f"background-color: {colors[crease]}; color: white; padding: 5px; font-weight: bold;")
                self.measurements_layout.addWidget(header)

                # Distances (sequential: p0→p1, p1→p2, etc.)
                for dist_info in crease_distances:
                    dist_text = (f"  p{dist_info['from_point']} → p{dist_info['to_point']}: "
                                f"{dist_info['cm_distance']:.2f} cm "
                                f"({dist_info['pixel_distance']:.1f} px)")
                    dist_label = QLabel(dist_text)
                    dist_label.setStyleSheet(f"padding: 3px; border-left: 3px solid {colors[crease]}; font-family: monospace;")
                    self.measurements_layout.addWidget(dist_label)

        if not has_measurements:
            empty_label = QLabel("Add crease points to see measurements")
            empty_label.setStyleSheet("color: gray; font-style: italic; padding: 10px;")
            self.measurements_layout.addWidget(empty_label)

        self.measurements_layout.addStretch()

    def toggle_view_mode(self):
        """Toggle between image view and plot view."""
        if self.view_mode == "image":
            # Switch to plot view
            self.canvas.hide()
            self.plot_canvas.show()
            self.view_mode = "plot"
            self.view_toggle_btn.setText("🖼️ Switch to Image View")
            self.view_toggle_btn.setStyleSheet("background-color: #FF5722; color: white; font-weight: bold; font-size: 11px; padding: 8px; border-radius: 5px;")
            # Update plot when switching to it
            self.update_geometric_plot()
        else:
            # Switch to image view
            self.plot_canvas.hide()
            self.canvas.show()
            self.view_mode = "image"
            self.view_toggle_btn.setText("📊 Switch to Plot View")
            self.view_toggle_btn.setStyleSheet("background-color: #9C27B0; color: white; font-weight: bold; font-size: 11px; padding: 8px; border-radius: 5px;")

    def update_geometric_plot(self):
        """Update geometric plot showing segment centers and connections in CAD style with cm units."""
        self.figure.clear()

        # Set dark background for CAD style
        self.figure.patch.set_facecolor('#1a1a1a')
        ax = self.figure.add_subplot(111)
        ax.set_facecolor('#0a0a0a')

        landmarks = self.canvas.get_landmarks()
        crease1_points = landmarks.get('crease1', [])
        crease2_points = landmarks.get('crease2', [])

        # Check if calibration is available
        if not self.canvas.measurement_calc.scale_calibrated:
            ax.text(0.5, 0.5, 'Please load an image with\nAprilTag for calibration',
                   ha='center', va='center', fontsize=14, color='#00ff00',
                   transform=ax.transAxes, weight='bold')
            ax.set_xlim(0, 1)
            ax.set_ylim(0, 1)
            ax.axis('off')
            self.plot_canvas.draw()
            return

        # We need at least 6 points (3 segments) from each crease
        if len(crease1_points) < 6 or len(crease2_points) < 6:
            ax.text(0.5, 0.5, 'Need at least 6 points in\nCrease 1 and Crease 2\n(3 segments each)',
                   ha='center', va='center', fontsize=14, color='#00ff00',
                   transform=ax.transAxes, weight='bold')
            ax.set_xlim(0, 1)
            ax.set_ylim(0, 1)
            ax.axis('off')
            self.plot_canvas.draw()
            return

        # Get pixels per cm for conversion
        pixels_per_cm = self.canvas.measurement_calc.pixels_per_cm

        # Convert pixel coordinates to cm
        def pixels_to_cm(points):
            """Convert list of pixel coordinates to cm."""
            cm_points = []
            for x, y in points:
                cm_x = x / pixels_per_cm
                cm_y = y / pixels_per_cm
                cm_points.append((cm_x, cm_y))
            return cm_points

        crease1_cm = pixels_to_cm(crease1_points)
        crease2_cm = pixels_to_cm(crease2_points)

        # Extract first 3 segments (index, middle, ring fingers)
        # seg1: p0-p1, seg2: p2-p3, seg3: p4-p5
        def get_segments(points):
            """Extract first 3 segments and their centers."""
            segments = []
            centers = []
            for i in range(0, 6, 2):  # 0, 2, 4
                if i + 1 < len(points):
                    p0 = np.array(points[i])
                    p1 = np.array(points[i + 1])
                    center = (p0 + p1) / 2.0
                    segments.append((p0, p1))
                    centers.append(center)
            return segments, centers

        crease1_segs, crease1_centers = get_segments(crease1_cm)
        crease2_segs, crease2_centers = get_segments(crease2_cm)

        # Plot crease 1 segments and centers (Cyan - CAD style)
        for i, (p0, p1) in enumerate(crease1_segs):
            ax.plot([p0[0], p1[0]], [p0[1], p1[1]], color='#00ffff', linewidth=3, alpha=0.8, label=f'C1 Seg{i+1}' if i == 0 else '')
            ax.plot(p0[0], p0[1], 'o', color='#00ffff', markersize=8)
            ax.plot(p1[0], p1[1], 'o', color='#00ffff', markersize=8)

        # Plot crease 1 center connections
        if len(crease1_centers) >= 2:
            centers_array = np.array(crease1_centers)
            ax.plot(centers_array[:, 0], centers_array[:, 1], '--', color='#00ffff', linewidth=2, alpha=0.6, label='C1 Centers')
            for center in crease1_centers:
                ax.plot(center[0], center[1], 's', color='#00ffff', markersize=10)

        # Plot crease 2 segments and centers (Yellow - CAD style)
        for i, (p0, p1) in enumerate(crease2_segs):
            ax.plot([p0[0], p1[0]], [p0[1], p1[1]], color='#ffff00', linewidth=3, alpha=0.8, label=f'C2 Seg{i+1}' if i == 0 else '')
            ax.plot(p0[0], p0[1], 'o', color='#ffff00', markersize=8)
            ax.plot(p1[0], p1[1], 'o', color='#ffff00', markersize=8)

        # Plot crease 2 center connections
        if len(crease2_centers) >= 2:
            centers_array = np.array(crease2_centers)
            ax.plot(centers_array[:, 0], centers_array[:, 1], '--', color='#ffff00', linewidth=2, alpha=0.6, label='C2 Centers')
            for center in crease2_centers:
                ax.plot(center[0], center[1], 's', color='#ffff00', markersize=10)

        # Add segment labels
        segment_labels = ['Index', 'Middle', 'Ring']
        for i, center in enumerate(crease1_centers):
            if i < len(segment_labels):
                ax.text(center[0], center[1] - 0.3, segment_labels[i],
                       ha='center', fontsize=11, color='#00ffff', weight='bold')

        # Add dimension annotations for Crease 1 (along crease)
        for i in range(len(crease1_centers) - 1):
            c1 = crease1_centers[i]
            c2 = crease1_centers[i + 1]
            dist = float(np.linalg.norm(c2 - c1))
            mid = (c1 + c2) / 2
            ax.text(mid[0], mid[1] + 0.3, f'C1: {dist:.2f} cm',
                   ha='center', fontsize=9, color='#00ffff', weight='bold',
                   bbox=dict(boxstyle='round,pad=0.3', facecolor='black', edgecolor='#00ffff', linewidth=1))

        # Add dimension annotations for Crease 2 (along crease)
        for i in range(len(crease2_centers) - 1):
            c1 = crease2_centers[i]
            c2 = crease2_centers[i + 1]
            dist = float(np.linalg.norm(c2 - c1))
            mid = (c1 + c2) / 2
            ax.text(mid[0], mid[1] - 0.3, f'C2: {dist:.2f} cm',
                   ha='center', fontsize=9, color='#ffff00', weight='bold',
                   bbox=dict(boxstyle='round,pad=0.3', facecolor='black', edgecolor='#ffff00', linewidth=1))

        # Add cross-crease connections (c1:seg1 to c2:seg1, etc.)
        if len(crease1_centers) == 3 and len(crease2_centers) == 3:
            vertical_mids = []
            vertical_vectors = []

            for i in range(3):  # seg1, seg2, seg3
                c1_center = crease1_centers[i]
                c2_center = crease2_centers[i]

                # Draw connection line (magenta/pink for cross-crease)
                ax.plot([c1_center[0], c2_center[0]], [c1_center[1], c2_center[1]],
                       color='#ff00ff', linewidth=2, alpha=0.6, linestyle=':')

                # Calculate and display distance
                dist = float(np.linalg.norm(c2_center - c1_center))
                mid = (c1_center + c2_center) / 2
                vertical_mids.append(mid)
                vertical_vectors.append(c2_center - c1_center)

                # Offset text based on segment to avoid overlap
                offset_x = 0.5 if i == 1 else -0.5 if i == 0 else 0.5
                ax.text(mid[0] + offset_x, mid[1], f'{dist:.2f} cm',
                       ha='center', fontsize=9, color='#ff00ff', weight='bold',
                       bbox=dict(boxstyle='round,pad=0.3', facecolor='black', edgecolor='#ff00ff', linewidth=1))

            # --- Angle Calculation & Visualization ---
            vertical_mids = np.array(vertical_mids)

            # Draw Reference Lines (connecting vertical midpoints)
            # Line 1-2 (Index Mid -> Middle Mid)
            ax.plot([vertical_mids[0][0], vertical_mids[1][0]], 
                    [vertical_mids[0][1], vertical_mids[1][1]], 
                    color='white', linestyle='-.', linewidth=1.5, alpha=0.7, label='Ref Line 1-2')
            
            # Line 2-3 (Middle Mid -> Ring Mid)
            ax.plot([vertical_mids[1][0], vertical_mids[2][0]], 
                    [vertical_mids[1][1], vertical_mids[2][1]], 
                    color='white', linestyle='-.', linewidth=1.5, alpha=0.7, label='Ref Line 2-3')

            # Calculate Angles
            def get_angle(v1, v2):
                u1 = v1 / np.linalg.norm(v1)
                u2 = v2 / np.linalg.norm(v2)
                return np.degrees(np.arccos(np.clip(np.dot(u1, u2), -1.0, 1.0)))

            ref_12 = vertical_mids[1] - vertical_mids[0]
            ref_23 = vertical_mids[2] - vertical_mids[1]

            ang1 = get_angle(vertical_vectors[0], ref_12)
            ang2 = 180 - get_angle(vertical_vectors[1], ref_12) 
            ang3 = get_angle(vertical_vectors[1], ref_23)
            ang4 = 180 - get_angle(vertical_vectors[2], ref_23) 

            # Display Angles in a box on the plot
            angle_text = (
                f"ANGLES:\n"
                f"Ang1 (V1/Ref1-2): {ang1:.1f}°\n"
                f"Ang2 (V2/Ref1-2): {ang2:.1f}°\n"
                f"Ang3 (V2/Ref2-3): {ang3:.1f}°\n"
                f"Ang4 (V3/Ref2-3): {ang4:.1f}°"
            )
            ax.text(0.02, 0.98, angle_text, transform=ax.transAxes,
                    fontsize=9, color='white', verticalalignment='top', family='monospace',
                    bbox=dict(boxstyle='round', facecolor='#222222', alpha=0.8, edgecolor='white'))

        ax.set_xlabel('X (cm)', fontsize=12, color='#00ff00', weight='bold')
        ax.set_ylabel('Y (cm)', fontsize=12, color='#00ff00', weight='bold')
        ax.set_title('CAD-Style Crease Segment Geometry\n(Cyan: Crease 1, Yellow: Crease 2)',
                    fontsize=13, color='#00ff00', weight='bold', pad=20)

        # CAD-style legend
        legend = ax.legend(loc='upper right', fontsize=10, facecolor='#1a1a1a',
                          edgecolor='#00ff00', framealpha=0.9)
        for text in legend.get_texts():
            text.set_color('#00ff00')

        # CAD-style grid
        ax.grid(True, alpha=0.3, color='#00ff00', linestyle='--', linewidth=0.5)
        ax.tick_params(colors='#00ff00', which='both')
        for spine in ax.spines.values():
            spine.set_edgecolor('#00ff00')
            spine.set_linewidth(2)

        ax.invert_yaxis()  # Invert Y axis to match image coordinates
        ax.set_aspect('equal', adjustable='box')

        self.figure.tight_layout()
        self.plot_canvas.draw()

    def undo_point(self):
        """Undo last point."""
        self.canvas.undo_last_point()
        self.update_point_counter()
        self.update_landmarks_display()
        self.update_measurements_display()

    def clear_current_crease(self):
        """Clear points for current crease."""
        if self.canvas.current_crease:
            reply = QMessageBox.question(
                self, "Confirm",
                f"Clear all points for {self.canvas.current_crease}?"
            )
            if reply == QMessageBox.Yes:
                self.canvas.clear_crease()
                self.update_point_counter()
                self.update_landmarks_display()
                self.update_measurements_display()

    def clear_all(self):
        """Clear all points."""
        reply = QMessageBox.question(
            self, "Confirm",
            "Clear all landmarks for all creases?"
        )
        if reply == QMessageBox.Yes:
            self.canvas.clear_all()
            self.update_point_counter()
            self.update_landmarks_display()
            self.update_measurements_display()

    def save_landmarks(self):
        """Save landmarks to JSON file with measurements."""
        landmarks = self.canvas.get_landmarks()

        # Check if any creases have no points
        empty_creases = [c for c, p in landmarks.items() if len(p) == 0]

        if len(empty_creases) == 3:
            QMessageBox.warning(
                self, "No Data",
                "No points have been added. Please add points before saving."
            )
            return

        # Save dialog
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Landmarks", "hand_crease_landmarks",
            "JSON Files (*.json)"
        )

        if file_path:
            try:
                # Format: crease_finger_index (e.g., crease1_0 = crease 1, thumb)
                formatted_data = {}
                for crease, points in landmarks.items():
                    for idx, (x, y) in enumerate(points):
                        key = f"{crease}_{idx}"
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

    def save_analysis_csv(self):
        """Save geometric analysis (angles and distances) to CSV."""
        landmarks = self.canvas.get_landmarks()
        crease1_points = landmarks.get('crease1', [])
        crease2_points = landmarks.get('crease2', [])

        if len(crease1_points) < 6 or len(crease2_points) < 6:
            QMessageBox.warning(self, "Insufficient Data", "Need at least 6 points in Crease 1 and Crease 2.")
            return

        if not self.canvas.measurement_calc.scale_calibrated:
            QMessageBox.warning(self, "No Calibration", "Please calibrate scale using AprilTag first.")
            return

        # Prepare CSV file
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Analysis", "hand_analysis", "CSV Files (*.csv)"
        )

        if not file_path:
            return

        try:
            pixels_per_cm = self.canvas.measurement_calc.pixels_per_cm

            # Helper to convert to cm
            def to_cm(p):
                return np.array([p[0] / pixels_per_cm, p[1] / pixels_per_cm])

            # Extract segments and calculate centers (in cm)
            centers_c1 = []
            centers_c2 = []
            for i in range(0, 6, 2):
                p1_c1 = to_cm(crease1_points[i])
                p2_c1 = to_cm(crease1_points[i+1])
                centers_c1.append((p1_c1 + p2_c1) / 2.0)

                p1_c2 = to_cm(crease2_points[i])
                p2_c2 = to_cm(crease2_points[i+1])
                centers_c2.append((p1_c2 + p2_c2) / 2.0)

            # Midpoints of verticals (P1, P2, P3)
            P = []
            Verticals = [] # Vectors for verticals (C1 -> C2)
            for i in range(3):
                c1 = centers_c1[i]
                c2 = centers_c2[i]
                P.append((c1 + c2) / 2.0)
                Verticals.append(c2 - c1)

            # Reference Lines vectors
            Ref12 = P[1] - P[0]
            Ref23 = P[2] - P[1]

            # Calculate Angles (in degrees)
            def calc_angle(v1, v2):
                # Angle between two vectors
                unit_v1 = v1 / np.linalg.norm(v1)
                unit_v2 = v2 / np.linalg.norm(v2)
                dot_product = np.dot(unit_v1, unit_v2)
                angle = np.degrees(np.arccos(np.clip(dot_product, -1.0, 1.0)))
                return angle

            ang1 = calc_angle(Verticals[0], Ref12)
            ang2 = calc_angle(Verticals[1], Ref12)
            ang3 = calc_angle(Verticals[1], Ref23)
            ang4 = calc_angle(Verticals[2], Ref23)

            # Write to CSV
            with open(file_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['Metric', 'Value', 'Unit', 'Description'])
                writer.writerow(['Angle 1', f"{ang1:.2f}", 'degrees', 'Vertical 1 (Index) vs Line 1-2'])
                writer.writerow(['Angle 2', f"{ang2:.2f}", 'degrees', 'Vertical 2 (Middle) vs Line 1-2'])
                writer.writerow(['Angle 3', f"{ang3:.2f}", 'degrees', 'Vertical 2 (Middle) vs Line 2-3'])
                writer.writerow(['Angle 4', f"{ang4:.2f}", 'degrees', 'Vertical 3 (Ring) vs Line 2-3'])
                
                # Add distances for context
                writer.writerow([])
                writer.writerow(['Segment Distances', '', '', ''])
                # C1 Segments
                for i in range(len(centers_c1)-1):
                    dist = np.linalg.norm(centers_c1[i+1] - centers_c1[i])
                    writer.writerow([f'C1 Seg {i+1}-{i+2}', f"{dist:.2f}", 'cm', 'Along Crease 1'])
                
                # C2 Segments
                for i in range(len(centers_c2)-1):
                    dist = np.linalg.norm(centers_c2[i+1] - centers_c2[i])
                    writer.writerow([f'C2 Seg {i+1}-{i+2}', f"{dist:.2f}", 'cm', 'Along Crease 2'])

                # Verticals
                for i in range(3):
                    dist = np.linalg.norm(centers_c2[i] - centers_c1[i])
                    writer.writerow([f'Vertical {i+1}', f"{dist:.2f}", 'cm', f'Cross-Crease {i+1}'])

            QMessageBox.information(self, "Success", f"Analysis saved to:\n{file_path}")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save analysis: {str(e)}")

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
