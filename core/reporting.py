import cv2
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Dict

from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from PIL import Image as PILImage

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
