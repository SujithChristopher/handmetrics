# Hand Pose and AprilTag Detection

Professional tools for hand pose detection and manual landmark annotation with AprilTag support.

## 🎯 Quick Start

### Installation

```bash
# Install all dependencies
pip install -r requirements.txt
```

### Two Approaches

#### 1. Automatic Detection (Fast)
```bash
python hand_pose_apriltag_detector.py
```
- ✅ Fast automatic detection using MediaPipe
- ✅ Saves plots to `plots/` folder
- ❌ May have accuracy issues with certain hand positions

#### 2. Manual Annotation GUI (Accurate)
```bash
python hand_annotation_gui.py
```
- ✅ Precise manual landmark annotation
- ✅ Visual feedback and real-time updates
- ✅ AprilTag detection included
- ✅ Save to JSON format

---

## 📋 Tools Overview

### 1. Automatic Hand Pose Detection
**File:** `hand_pose_apriltag_detector.py`

Automatically detects hand poses and AprilTag markers in batch.

**Features:**
- MediaPipe-based hand detection
- AprilTag detection (tag36h11)
- Batch processing of multiple images
- Matplotlib visualization with color-coded landmarks
- Console output with detection statistics

**Usage:**
```bash
python hand_pose_apriltag_detector.py
```

**Output:** PNG plots saved to `plots/detected_*.png`

---

### 2. Manual Hand Joint Annotation GUI
**File:** `hand_annotation_gui.py`

Interactive GUI for precise manual annotation of hand landmarks with visual feedback.

**Features:**
- **Finger-by-Finger Selection**: Annotate one finger at a time
- **4 Points Per Finger**: Start (base), Joint 1, Joint 2, End (tip)
- **Real-time Visualization**: See points overlaid on image
- **AprilTag Auto-Detection**: Automatic detection and display
- **Point Tracking**: Counter shows progress (X/4)
- **Undo/Clear Functions**: Correct mistakes easily
- **JSON Export**: Save landmarks in structured format
- **Single Hand Mode**: Focused on one hand per session

**Supported Fingers:**
- Thumb
- Index
- Middle
- Ring
- Pinky

**Usage:**
```bash
python hand_annotation_gui.py
```

**Output:** JSON file with landmarks and AprilTag info

---

### 3. Landmark Viewer Utility
**File:** `view_landmarks.py`

View and visualize saved hand landmarks.

**Usage:**
```bash
python view_landmarks.py hand_landmarks.json
```

**Output:**
- Displays image with landmarks overlaid
- Prints detailed coordinate information
- Shows detected AprilTags

---

### 4. Format Converter
**File:** `convert_landmarks.py`

Convert manual annotations to MediaPipe format.

**Usage:**
```bash
python convert_landmarks.py hand_landmarks.json hand_landmarks_mediapipe.json
```

**Converts:**
- Manual format (4 points per finger) → MediaPipe format (21 landmarks)
- Normalizes coordinates to [0.0, 1.0] range

---

## 📁 Project Structure

```
hand_pose/
├── images/                              # Input images
│   ├── WhatsApp Image 2025-10-30 at 17.30.34.jpeg
│   └── WhatsApp Image 2025-10-30 at 17.30.57.jpeg
├── plots/                               # Auto-detection output (created automatically)
├── hand_pose_apriltag_detector.py       # Auto-detection script
├── hand_annotation_gui.py               # Manual annotation GUI ⭐ NEW
├── view_landmarks.py                    # Landmark viewer utility
├── convert_landmarks.py                 # Format converter
├── requirements.txt                     # Dependencies
├── README.md                            # This file
└── README_GUI.md                        # Detailed GUI documentation
```

---

## 🖼️ GUI Interface Design

```
┌─────────────────────────────────────────────────────────────┐
│ Hand Joint Annotation Tool                                  │
├──────────────┬──────────────────────────┬──────────────────┤
│  CONTROLS    │    IMAGE CANVAS          │   LANDMARKS      │
│              │                          │                  │
│ Load Image   │                          │ AprilTags:       │
│              │ Click to add joints      │ - ID: 11         │
│ Select       │                          │                  │
│ Finger ▼     │ [Image with Points]      │ Thumb (3/4)      │
│ Thumb        │                          │ - Start: (100,200)
│              │ • Green = fingers        │ - Joint1: (110,190)
│ Point        │ • Lines = skeleton       │ - Joint2: (120,180)
│ Counter      │ • Green box = AprilTag   │                  │
│ 3 / 4        │                          │ Index (0/4)      │
│              │                          │ Middle (0/4)     │
│ [Undo]       │                          │ Ring (0/4)       │
│ [Clear Fngr] │                          │ Pinky (0/4)      │
│ [Clear All]  │                          │                  │
│              │                          │ [Scroll]         │
│ [Save] ✓     │                          │                  │
└──────────────┴──────────────────────────┴──────────────────┘
```

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

| Finger | Color | Purpose |
|--------|-------|---------|
| Thumb | Blue | Easy identification |
| Index | Green | Natural association |
| Middle | Red | Distinct from others |
| Ring | Cyan | Unique color |
| Pinky | Magenta | Unique color |

---

## 🔧 GUI Workflow

### Step-by-Step Process

1. **Load Image**
   - Click "Load Image"
   - AprilTags auto-detected
   - Image displays with detection results

2. **Select Finger**
   - Choose from dropdown (Thumb, Index, Middle, Ring, Pinky)
   - Single hand mode only

3. **Annotate (Click on Image)**
   - **Point 0**: Start (wrist/palm base)
   - **Point 1**: Joint 1 (MCP)
   - **Point 2**: Joint 2 (PIP)
   - **Point 3**: End (fingertip)

4. **Monitor Progress**
   - Counter shows X/4
   - Coordinates displayed in right panel
   - Points shown on image in real-time

5. **Corrections**
   - Undo: Remove last point
   - Clear Current: Clear finger's points
   - Clear All: Start over

6. **Save**
   - Click "Save Landmarks"
   - Choose filename
   - Saves as JSON with all data

---

## 📦 Dependencies

```
opencv-python>=4.7.0       # Image processing and ArUco detection
mediapipe>=0.10.0          # Hand detection (auto-detection only)
PySide6>=6.5.0             # GUI framework (annotation tool only)
numpy>=1.21.0              # Numerical operations
matplotlib>=3.5.0          # Plotting and visualization
apriltag>=0.2.0            # AprilTag detection (optional)
```

Install all at once:
```bash
pip install -r requirements.txt
```

---

## 🚀 Usage Examples

### Example 1: Automatic Detection with Visualization

```bash
python hand_pose_apriltag_detector.py
# Output: plots/detected_image_name.png
```

### Example 2: Manual Annotation

```bash
python hand_annotation_gui.py
# 1. Load image from images/ folder
# 2. Select finger (e.g., "Index")
# 3. Click 4 times on image to mark joints
# 4. Repeat for other fingers
# 5. Save as hand_landmarks.json
```

### Example 3: View Saved Landmarks

```bash
python view_landmarks.py hand_landmarks.json
# Displays image with landmarks overlaid
# Prints all coordinates to console
```

### Example 4: Convert to MediaPipe Format

```bash
python convert_landmarks.py hand_landmarks.json hand_landmarks_mediapipe.json
# Output: MediaPipe-compatible format
```

---

## 📝 Output Files

### From Auto-Detection
- `plots/detected_*.png` - High-quality visualization plots

### From Manual Annotation
- `hand_landmarks.json` - Coordinates and AprilTag info

### From Format Conversion
- `hand_landmarks_mediapipe.json` - MediaPipe format (21 landmarks)

---

## ✅ Checklist: When to Use Each Tool

### Use Auto-Detection When:
- ✅ Quick results needed
- ✅ Hand is in clear, well-lit conditions
- ✅ Standard hand positions
- ✅ Batch processing multiple images
- ✅ Testing/validation phase

### Use Manual Annotation When:
- ✅ High accuracy required
- ✅ Hand in complex poses
- ✅ Difficult lighting conditions
- ✅ Specific landmark precision needed
- ✅ Dataset creation/labeling
- ✅ Validation of auto-detection

---

## 🐛 Troubleshooting

### GUI Won't Launch
```bash
pip install --upgrade PySide6
python hand_annotation_gui.py
```

### Import Errors
```bash
# Check all dependencies installed
pip install -r requirements.txt --upgrade
```

### Image Won't Load
- Ensure image is in `images/` folder
- Check supported formats (.jpg, .png, .bmp)
- Verify file permissions

### AprilTag Not Detected
- Ensure tag is clearly visible
- Good lighting is important
- Tag should be roughly square to camera
- Minimum size: 50x50 pixels recommended

### Save Fails
- Check write permissions in directory
- Ensure sufficient disk space
- Try saving to different location

---

## 📚 Additional Resources

For detailed GUI documentation, see [README_GUI.md](README_GUI.md)

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

1. **For Accuracy**: Use manual annotation for important datasets
2. **For Speed**: Use auto-detection for quick previews
3. **For Validation**: Use auto-detection followed by manual verification
4. **For Consistency**: Use the same finger order for all images
5. **For Quality**: Ensure consistent lighting and image quality

---

**Version**: 2.0 (GUI Added)
**Last Updated**: 2025-11-12
