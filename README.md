# HandMetrics

Professional hand joint annotation and measurement system with AprilTag calibration. Generate comprehensive PDF reports of hand measurements with visual annotations.

## 🎯 Quick Start

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd handmetrics

# Install dependencies (Python 3.13+)
pip install -r requirements.txt

# Run the application
python main.py
```

### Key Features

#### HandMetrics GUI (Primary Tool)
```bash
python main.py
```
- ✅ Real-time hand joint annotation (6 points per crease)
- ✅ AprilTag auto-detection for pixel-to-cm conversion
- ✅ **Geometric Analysis View**: CAD-style plot showing angles and segment centers
- ✅ **CSV Export**: Clinical analysis data (IB1_ANG, MI_LEN, etc.)
- ✅ **Generate professional PDF reports** with annotated images and measurements
- ✅ Professional A4 PDF format, single-page output
- ✅ Reports saved to `Documents/HandMetrics/reports/`

---

## 📋 Main Application

### HandMetrics GUI
**File:** `main.py`

Complete hand annotation and measurement system with PDF report generation.

**Features:**
- **Real-time Annotation**: Click to place hand joint landmarks
- **Finger Selection**: Choose from 5 fingers (Thumb, Index, Middle, Ring, Pinky)
- **4 Points Per Finger**: Annotate Start, Joint 1, Joint 2, and End (Tip)
- **AprilTag Calibration**: Automatic detection for accurate pixel-to-cm conversion
- **Measurement Display**: Real-time measurement overlay on image
- **📄 PDF Reports**: Generate professional A4 reports with:
  - Annotated image (with all landmarks and measurements visible)
  - Joint distance measurements (in cm and pixels)
  - Scale calibration information
  - Image metadata and timestamp
- **Point Management**:
  - Undo last point
  - Clear current finger points
  - Clear all landmarks
- **Single Hand Mode**: Focused on one hand per annotation session

- **Crease 1**: Proximal crease (Cyan) - use 6 points (Index, Middle, Ring segments)
- **Crease 2**: Distal crease (Yellow) - use 6 points (Index, Middle, Ring segments)
- **Crease 3**: Optional third crease (Red)

**Usage:**
```bash
python main.py
```

**Output:**
- PDF Reports saved to `~/Documents/HandMetrics/reports/HandMetrics_*.pdf`

**Report Format:**
- A4 page size (single page)
- Professional styling
- Includes annotated image showing landmarks and measurements
- Joint distance measurements table
- Scale calibration info

---

## 📁 Project Structure

```
handmetrics/
├── core/                # 🧠 Business Logic
│   ├── measurement.py   # MeasurementCalculator (Scale & Calibration)
│   └── reporting.py     # ReportGenerator (PDF Logic)
├── widgets/             # 🎨 UI Components
│   └── image_canvas.py  # ImageCanvas (Drawing & Detection)
├── ui/                  # 🖼️ Application Windows
│   └── main_window.py   # HandAnnotationWithMeasurements (Main UI)
├── images/              # Input images folder
├── main.py              # ⭐ Clean Entry Point
├── requirements.txt     # Python dependencies
└── ...
```

---

## 🖼️ GUI Interface Design

```
┌─────────────────────────────────────────────────────────────────┐
│ HandMetrics - Hand Joint Annotation Tool                        │
├──────────────┬───────────────────────────────┬────────────────┤
│  CONTROLS    │    IMAGE CANVAS               │   DATA DISPLAY │
│              │                               │                │
│ Load Image   │                               │ ┌─ Landmarks ─┐
│              │ Click to add joints           │ │ AprilTags:   │
│ Select       │                               │ │ - ID: 11     │
│ Finger ▼     │ [Image with Points]           │ │              │
│ (Blank)      │                               │ │ Thumb (3/4)  │
│              │ • Blue = thumb                │ │ - Start      │
│ Point        │ • Green = index               │ │ - Joint 1    │
│ Counter      │ • Red = middle                │ │ - Joint 2    │
│ 3 / 4        │ • Cyan = ring                 │ │ - End        │
│              │ • Magenta = pinky             │ │              │
│ Measurements │ • Lines = connections         │ └──────────────┘
│ ✓ Calibrated │ • Green box = AprilTag        │ ┌─ Measurements─┐
│ • 5.34 px/cm │ • Distances in cm             │ │ Thumb         │
│              │                               │ │ J0→1: 2.65 cm │
│ [Undo]       │                               │ │ J1→2: 3.12 cm │
│ [Clear Fngr] │                               │ │ J2→3: 2.41 cm │
│ [Clear All]  │                               │ │ Index         │
│              │                               │ │ J0→1: 2.89 cm │
│ [Generate    │                               │ │ ...            │
│  Report PDF] │                               │ └──────────────┘
└──────────────┴───────────────────────────────┴────────────────┘
```

**Three-Panel Layout:**
- **Left (20%)**: Controls and measurements
- **Center (60%)**: Image canvas with annotations
- **Right (20%)**: Data display with tabs for Landmarks & Measurements

---

## 📊 Hand Landmarks Structure

### Manual Annotation Format (4 points per finger)

```json
{
  "image_path": "images/hand.jpg",
  "thumb_0": {"x": 100, "y": 200},
  "thumb_1": {"x": 110, "y": 190},
  "thumb_2": {"x": 120, "y": 180},
  "thumb_3": {"x": 130, "y": 170},
  "index_0": {"x": 150, "y": 210},
  ...
  "apriltags": [
    {"id": 11, "corners": [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]}
  ]
}
```

### MediaPipe Format (21 landmarks)

```
Landmark 0:  Wrist
Landmarks 1-4:  Thumb (MCP, PIP, DIP, Tip)
Landmarks 5-8:  Index (MCP, PIP, DIP, Tip)
Landmarks 9-12: Middle (MCP, PIP, DIP, Tip)
Landmarks 13-16: Ring (MCP, PIP, DIP, Tip)
Landmarks 17-20: Pinky (MCP, PIP, DIP, Tip)
```

---

## 🎨 Color Coding

| Feature | Label | Source |
|---------|-------|--------|
| Index Base 1 Angle | IB1_ANG | V1 (Index) vs Ref1-2 |
| Middle Base 1 Angle | MB1_ANG | V2 (Middle) vs -Ref1-2 |
| Middle Base 2 Angle | MB2_ANG | V2 (Middle) vs Ref2-3 |
| Ring Base 2 Angle | RB2_ANG | V3 (Ring) vs -Ref2-3 |
| Middle-Index Length | MI_LEN | Crease 2 Segment Distance |
| Middle-Ring Length | MR_LEN | Crease 2 Segment Distance |
| Crease 1 Segments | C1_SEG_X | Crease 1 Distances |

---

## 🔧 GUI Workflow

### Step-by-Step Process

1. **Load Image**
   - Click "Load Image"
   - AprilTag auto-detected
   - Image displays with calibration info

2. **Select Finger**
   - Choose from dropdown (Thumb, Index, Middle, Ring, Pinky)
   - Single hand mode only
   - Starts blank - select to begin

3. **Annotate (Click on Image)**
   - **Point 0**: Start (wrist/palm base)
   - **Point 1**: Joint 1 (MCP)
   - **Point 2**: Joint 2 (PIP)
   - **Point 3**: End (fingertip)

4. **Monitor Progress**
   - Counter shows X/4 for current finger
   - Measurements display in real-time
   - Points shown on image with color coding
   - Right panel shows landmarks and measurements

5. **Corrections**
   - **Undo**: Remove last point
   - **Clear Current**: Clear finger's points
   - **Clear All**: Start over with all fingers

6. **Generate Report**
   - Click "📄 Generate Report (PDF)"
   - Professional A4 PDF created automatically
   - Includes:
     - Annotated image with visible landmarks
     - Joint distance measurements
     - Scale calibration info
     - Timestamp and image details
   - Saved to `~/Documents/HandMetrics/reports/`

---

## 📦 Dependencies

**Python Version:** 3.13+

```
opencv-contrib-python>=4.12.0       # Image processing and AprilTag detection
PySide6>=6.5.0                      # GUI framework
numpy>=1.21.0                       # Numerical operations
matplotlib>=3.5.0                   # Visualization (utilities)
reportlab>=4.0.0                    # PDF report generation
Pillow>=10.0.0                      # Image processing for PDF
```

**Install all at once:**
```bash
pip install -r requirements.txt
```

**Platform Support:**
- ✅ Windows 10/11
- ✅ macOS
- ❌ Linux (untested)

---

## 🚀 Usage Examples

### Example 1: Launch HandMetrics Application

```bash
python main.py
```

The GUI window opens with three panels:
- **Left**: Controls and measurement info
- **Center**: Image canvas for annotation
- **Right**: Data display with tabs

### Example 2: Complete Annotation Workflow

```bash
# 1. Start application
python main.py

# 2. Click "Load Image" and select an image with AprilTag
# 3. Scale calibration happens automatically
# 4. Select "Thumb" from dropdown
# 5. Click 4 times on the image to mark thumb joints
# 6. Repeat for Index, Middle, Ring, Pinky fingers
# 7. Click "📄 Generate Report (PDF)"
# 8. PDF saved to ~/Documents/HandMetrics/reports/
```

### Example 3: Using Real-Time Measurements

```bash
# During annotation:
# 1. Check "Show Measurements" to see cm distances
# 2. Right panel displays all measurements
# 3. Distances update in real-time as you annotate
```

---

## 📝 Output Files

### PDF Reports
- **Location:** `~/Documents/HandMetrics/reports/`
- **Format:** `HandMetrics_[image_name]_[timestamp].pdf`
- **Contents:**
  - Annotated image with landmarks and measurements
  - Joint distance measurements table (cm and pixels)
  - Scale calibration information
  - Image metadata and timestamp
  - Professional A4 single-page format

### Example Report Filename
```
HandMetrics_hand_photo_20250112_143025.pdf
```

---

## ✅ Getting Started Checklist

Before using HandMetrics:

- ✅ Python 3.13+ installed
- ✅ All dependencies installed (`pip install -r requirements.txt`)
- ✅ Image with AprilTag (7×7 cm) prepared
- ✅ AprilTag clearly visible in image
- ✅ Good lighting for accurate detection
- ✅ Adequate disk space for PDF reports (~100KB per report)

### For Best Results:

- ✅ Use high-resolution images (1920×1080 or higher)
- ✅ Ensure AprilTag is perpendicular to camera
- ✅ Place AprilTag and hand in same view
- ✅ Annotate all 5 fingers for complete data
- ✅ Use consistent lighting for similar hand poses
- ✅ Keep hand still while annotating

---

## 🐛 Troubleshooting

### Application Won't Start
```bash
# Ensure all dependencies installed
pip install -r requirements.txt --upgrade

# Run with Python 3.13+
python --version  # Check version
python main.py
```

### GUI Won't Launch / Import Errors
```bash
# Reinstall PySide6
pip install --upgrade PySide6

# Verify all imports work
python -c "import cv2, PySide6, reportlab; print('OK')"
```

### Image Won't Load
- Ensure image is in `images/` folder or use file browser
- Check supported formats (.jpg, .jpeg, .png, .bmp)
- Verify file permissions (readable)
- Image should be at least 640×480

### AprilTag Not Detected
- Ensure AprilTag is clearly visible in image
- Good lighting is essential
- Tag should be roughly square/perpendicular to camera
- Minimum size: 50×50 pixels recommended
- Check that image contains a valid AprilTag (tag36h11)

### Scale Calibration Shows "No Scale"
- AprilTag must be detected first
- Load an image that contains the AprilTag
- Check AprilTag quality and visibility

### PDF Report Generation Fails
- Check that Documents/HandMetrics/reports folder exists (auto-created)
- Ensure sufficient disk space
- Verify at least one landmark point is added
- Check that AprilTag is detected (required for measurements)

### Permission Denied Errors on macOS
```bash
# Grant execute permission if needed
chmod +x main.py
python main.py
```

---

## 📚 Additional Resources

- **CLAUDE.md** - Development guide for contributors
- **GitHub CI/CD** - Automated testing on Windows and macOS
- **Release Workflow** - Automatic release creation on version tags

## 🔄 CI/CD Workflow

This project includes GitHub Actions workflows:

### CI Workflow (`.github/workflows/ci.yml`)
- Runs on every push and pull request to `main`
- Tests on Windows and macOS with Python 3.13
- Verifies dependencies and syntax

### Release Workflow (`.github/workflows/release.yml`)
- Triggers on version tags (`v*`)
- Creates GitHub releases automatically
- Includes release notes

---

## 🎓 Hand Joint Information

```
FINGER ANATOMY:
├── Wrist (Base)
├── MCP (Metacarpophalangeal) - Point 0 in annotation
├── PIP (Proximal Interphalangeal) - Point 1 in annotation
├── DIP (Distal Interphalangeal) - Point 2 in annotation
└── Tip (End) - Point 3 in annotation
```

---

## 📄 License

This project uses:
- **PySide6** (LGPL License)
- **OpenCV** (Apache 2.0)
- **MediaPipe** (Apache 2.0)
- **NumPy** (BSD License)

---

## 💡 Pro Tips

1. **Consistent Lighting**: Use even lighting to avoid shadows on hand
2. **AprilTag Placement**: Position AprilTag near hand but not covering it
3. **Perpendicular View**: Keep camera perpendicular to hand for accurate measurements
4. **High Resolution**: Use images with good resolution for precise landmarks
5. **PDF Organization**: Reports auto-saved - check Documents/HandMetrics/reports regularly
6. **Batch Processing**: Annotate multiple hands using separate annotation sessions

## 📊 Measurement Accuracy

- **Typical Accuracy**: ±0.2-0.3 cm
- **Depends on**:
  - AprilTag detection quality
  - Image resolution
  - Landmark precision
  - Lighting conditions

---

## 🤝 Contributing

To contribute improvements or report issues:

1. Check CLAUDE.md for development guidelines
2. Fork the repository
3. Create a feature branch
4. Test on both Windows and macOS
5. Submit a pull request

The CI/CD pipeline will automatically test your changes.

---

## 📄 License

This project uses:
- **PySide6** (LGPL License)
- **OpenCV** (Apache 2.0)
- **ReportLab** (Apache 2.0)
- **Pillow** (HPND License)
- **NumPy** (BSD License)

---

**Version**: 3.0 (PDF Reports & Measurements)
**Last Updated**: 2025-11-12
**Status**: Active Development ✨
