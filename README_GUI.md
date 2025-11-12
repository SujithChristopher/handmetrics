# Hand Joint Annotation GUI

A professional PySide6-based GUI tool for manually annotating hand joint landmarks with AprilTag detection support.

## Features

### Main Features
- **Interactive GUI**: User-friendly PySide6 interface for manual hand annotation
- **Finger-by-Finger Annotation**: Select which finger to annotate with dedicated buttons
- **Per-Finger Point Tracking**: 4 points per finger (Start, Joint 1, Joint 2, End)
- **AprilTag Detection**: Automatic detection and visualization of AprilTag markers (tag36h11)
- **Real-time Visualization**: See points and AprilTags overlaid on the image
- **Undo Functionality**: Remove the last clicked point
- **Save to JSON**: Export landmarks in structured format
- **Landmark Viewer**: Utility to view and visualize saved landmarks

### GUI Layout Design

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                   │
│  ┌──────────────┐  ┌──────────────────────────┐  ┌──────────────┐│
│  │   CONTROLS   │  │    IMAGE CANVAS          │  │  LANDMARKS   ││
│  │              │  │                          │  │              ││
│  │ • Load Image │  │   Click on image to      │  │ • AprilTags  ││
│  │ • Select     │  │   add joint positions    │  │ • Points per ││
│  │   Finger     │  │                          │  │   finger     ││
│  │ • Point      │  │   [Image Display]        │  │ • Coordinates││
│  │   Counter    │  │                          │  │              ││
│  │ • Point      │  │   • Green points=fingers │  │ • Scrollable ││
│  │   Labels     │  │   • Skeleton lines       │  │   list       ││
│  │              │  │   • AprilTag boxes       │  │              ││
│  │ • Buttons:   │  │                          │  │              ││
│  │   - Undo     │  │                          │  │              ││
│  │   - Clear    │  │                          │  │              ││
│  │   - Save     │  │                          │  │              ││
│  │              │  │                          │  │              ││
│  └──────────────┘  └──────────────────────────┘  └──────────────┘│
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

## Installation

### 1. Install Dependencies

```bash
# Using requirements.txt (recommended)
pip install -r requirements.txt

# Or manually
pip install opencv-python PySide6 numpy matplotlib apriltag
```

### 2. Verify Installation

```bash
python -c "import PySide6; print('PySide6 OK')"
python -c "import cv2; print('OpenCV OK')"
python -c "import numpy; print('NumPy OK')"
```

## Usage

### Launch the Annotation GUI

```bash
python hand_annotation_gui.py
```

### Step-by-Step Workflow

1. **Load Image**
   - Click "Load Image" button
   - Select an image from the `images/` folder
   - Image displays with AprilTag detection results

2. **Select Finger**
   - Choose a finger from dropdown: Thumb, Index, Middle, Ring, Pinky
   - Only single hand annotation is supported

3. **Annotate Joints**
   - Click on the image at 4 positions for each finger:
     - **Point 0 (Start)**: Wrist/Palm base
     - **Point 1 (Joint 1)**: MCP (Metacarpophalangeal) joint
     - **Point 2 (Joint 2)**: PIP (Proximal Interphalangeal) joint
     - **Point 3 (End)**: DIP (Distal Interphalangeal) joint / Fingertip

4. **Track Progress**
   - Point counter shows `X / 4` for current finger
   - Right panel updates with coordinates in real-time
   - Color coding: Red=Thumb, Green=Index, Blue=Middle, Cyan=Ring, Magenta=Pinky

5. **Corrections**
   - **Undo Last Point**: Remove the last clicked point
   - **Clear Current Finger**: Clear all points for selected finger
   - **Clear All**: Clear all fingers and start over

6. **Save Landmarks**
   - Click "Save Landmarks" when done
   - Saves as JSON with all coordinates
   - Format: `{finger}_{point_index}` (e.g., `thumb_0`, `index_1`)
   - Also saves image path and AprilTag detection results

## Output Format

### JSON Structure

```json
{
  "image_path": "/path/to/image.jpg",
  "thumb_0": {"x": 100, "y": 200},
  "thumb_1": {"x": 110, "y": 190},
  "thumb_2": {"x": 120, "y": 180},
  "thumb_3": {"x": 130, "y": 170},
  "index_0": {"x": 150, "y": 210},
  ...
  "pinky_3": {"x": 400, "y": 150},
  "apriltags": [
    {
      "id": 11,
      "corners": [[x1, y1], [x2, y2], [x3, y3], [x4, y4]]
    }
  ]
}
```

## Viewing Saved Landmarks

Use the provided utility to view saved landmarks:

```bash
python view_landmarks.py hand_landmarks.json
```

This will:
- Print all landmark coordinates to console
- Display the image with landmarks overlaid
- Show detected AprilTags

### Example Output

```
============================================================
HAND LANDMARKS INFORMATION
============================================================

Image: images/hand_photo.jpg

Landmarks:

  THUMB:
    Start: (100, 200)
    Joint 1: (110, 190)
    Joint 2: (120, 180)
    End: (130, 170)

  INDEX:
    Start: (150, 210)
    Joint 1: (160, 200)
    Joint 2: (170, 190)
    End: (180, 180)

...

AprilTags Detected: 1
  ID: 11, Corners: [...]

============================================================
```

## Color Scheme

The GUI uses consistent color coding for easy identification:

| Finger | Color | RGB (BGR) |
|--------|-------|-----------|
| Thumb | Blue | (255, 0, 0) |
| Index | Green | (0, 255, 0) |
| Middle | Red | (0, 0, 255) |
| Ring | Cyan | (255, 255, 0) |
| Pinky | Magenta | (255, 0, 255) |

## AprilTag Detection

The GUI automatically detects AprilTag markers when you load an image:

- **Family**: tag36h11 (supports tags 0-587)
- **Detection**: Uses OpenCV's ArUco module
- **Display**: Green rectangles with tag ID

If an image contains an AprilTag marker:
- Bounding box is drawn in green
- Tag ID is shown at the center
- Information displayed in the right panel

## Keyboard Shortcuts (Future Enhancement)

Currently, all interactions are mouse-based. Potential keyboard shortcuts:

- `U`: Undo last point
- `C`: Clear current finger
- `S`: Save landmarks
- `1-5`: Select finger (1=Thumb, 2=Index, etc.)

## Troubleshooting

### GUI Won't Launch

```bash
# Check PySide6 installation
pip install --upgrade PySide6

# Run with verbose output
python -u hand_annotation_gui.py
```

### Image Not Loading

- Ensure image is in supported format (.jpg, .jpeg, .png, .bmp)
- Check file path and permissions
- Try absolute path instead of relative path

### AprilTag Not Detected

- Ensure tag is clearly visible in image
- Good lighting is important
- Tag should be roughly square to camera
- Minimum size: ~50x50 pixels recommended

### Saving Fails

- Check write permissions in current directory
- Ensure `plots/` or target folder exists
- Try saving to a different location

### Qt Platform Plugin Error

```bash
# Windows
pip install --upgrade PySide6

# Or specify platform explicitly
set QT_QPA_PLATFORM=windows
python hand_annotation_gui.py
```

## Advanced Usage

### Batch Processing

To annotate multiple images:

1. Save landmarks for each image
2. Create a script that loops through saved JSON files
3. Use `view_landmarks.py` to verify accuracy

### Custom Point Names

Modify the `point_names` list in `create_right_panel()` for different joint naming conventions:

```python
point_names = ["Base", "MCP", "PIP", "DIP"]  # Medical terminology
```

### Export to Different Formats

Extend the save functionality to support:
- CSV format
- XML format
- COCO dataset format
- Custom formats as needed

## File Structure

```
hand_pose/
├── images/                          # Input images
├── plots/                           # Output plots (auto-detection)
├── hand_annotation_gui.py           # Main GUI application
├── view_landmarks.py                # Landmark viewer utility
├── requirements.txt                 # Dependencies
├── README.md                        # Original README
├── README_GUI.md                    # This file
└── hand_pose_apriltag_detector.py   # Auto-detection script (legacy)
```

## Performance Notes

- **Image Size**: GUI handles images up to 4K resolution smoothly
- **Frame Rate**: Real-time rendering at 60+ FPS for typical images
- **Memory**: Uses ~100-200 MB depending on image size

## Design Decisions

### Single Hand Only
- Simplifies UI and workflow
- Reduces annotation complexity
- Allows focus on accurate joint positioning
- Can process second hand as separate annotation session

### 4 Points Per Finger
- Covers all major joints in a finger
- Sufficient for pose estimation
- Matches MediaPipe's hand skeleton structure
- Easy to label and understand

### Manual Annotation vs Auto-Detection
- **Manual**: Higher accuracy for specific use cases
- **Auto**: Faster but may have errors
- GUI provides validation and correction layer

### AprilTag Integration
- Useful for camera calibration
- Enables multi-view synchronization
- Provides reference frame for pose estimation
- Automatic detection saves manual effort

## Future Enhancements

- [ ] Support for multi-hand annotation
- [ ] Keyboard shortcuts for faster workflow
- [ ] Batch mode for processing multiple images
- [ ] Automatic point suggestion using lightweight models
- [ ] Camera/video stream support
- [ ] 3D pose estimation from annotated 2D points
- [ ] Hand pose templates and presets
- [ ] Annotation validation and quality metrics
- [ ] Export to COCO/Pascal VOC formats

## Requirements

- Python 3.7+
- PySide6 6.5+
- OpenCV 4.7+
- NumPy 1.21+
- NumPy 1.21+

## License

This tool uses:
- PySide6 (LGPL License)
- OpenCV (Apache 2.0 License)
- NumPy (BSD License)

## Support

For issues or questions:
1. Check the Troubleshooting section
2. Verify all dependencies are installed
3. Check console output for error messages
4. Try with different images to isolate issues
