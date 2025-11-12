# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Hand joint annotation and measurement system using AprilTag (7×7 cm) as a reference scale for pixel-to-centimeter conversion. Supports manual annotation via PySide6 GUI with real-time measurements, automatic batch detection via MediaPipe, and analysis tools for processing multiple annotated images.

**Key Constraint:** Single hand only per annotation session.

## Architecture

### Three-Tier System

```
Tier 1: GUI Applications (PySide6)
├── hand_annotation_gui.py          (basic annotation)
└── hand_annotation_with_measurements.py  (annotation + real-time measurements)

Tier 2: Core Detection (OpenCV/MediaPipe)
├── hand_pose_apriltag_detector.py  (batch auto-detection)
└── MeasurementCalculator class     (pixel-to-cm conversion)

Tier 3: Utilities
├── analyze_measurements.py         (batch analysis)
├── view_landmarks.py              (visualization viewer)
└── convert_landmarks.py           (format conversion)
```

### Key Classes

**MeasurementCalculator** (`hand_annotation_with_measurements.py`)
- Calibrates pixel-to-cm ratio from AprilTag corners
- Stores: `pixels_per_cm` = average_tag_edge_pixels / 7.0
- Converts any pixel distance to cm via division

**ImageCanvas** (custom QFrame)
- Handles mouse clicks → converts to original image pixel coordinates (not widget coords)
- Stores: `selected_points[finger] = [(x1,y1), (x2,y2), ...]` (image pixels)
- Manages AprilTag detection and visualization

### Coordinate System (Critical)

When user clicks on the zoomed/scaled displayed image:
```python
# PySide widget click position
canvas_pos = event.position()  # Widget coordinates

# Convert to original image coordinates
scale_x = self.image.shape[1] / self.display_image.width()
scale_y = self.image.shape[0] / self.display_image.height()
x = int(canvas_pos.x() * scale_x)
y = int(canvas_pos.y() * scale_y)

# All stored points are in ORIGINAL IMAGE PIXEL SPACE
self.selected_points[finger].append((x, y))
```

**Important:** All measurements use original image pixels, not display pixels.

## Common Commands

### Setup
```bash
pip install -r requirements.txt
```

### Main Applications

**Launch interactive annotation with measurements (recommended)**
```bash
python hand_annotation_with_measurements.py
```

**Launch basic annotation (without measurements)**
```bash
python hand_annotation_gui.py
```

**Batch auto-detection on all images in `images/` folder**
```bash
python hand_pose_apriltag_detector.py
```

### Analysis & Utilities

**View saved landmarks with overlay visualization**
```bash
python view_landmarks.py path/to/hand_landmarks.json
```

**Analyze multiple saved JSON files, generate statistics**
```bash
python analyze_measurements.py file1.json file2.json file3.json
# Outputs: hand_measurements_analysis.csv, hand_measurements_summary.json
```

**Convert manual format to MediaPipe format**
```bash
python convert_landmarks.py input.json output.json
```

## Data Flow

### Annotation Workflow
1. Load image → AprilTag auto-detected → `MeasurementCalculator.calibrate_from_apriltag()`
2. Select finger from dropdown → Set `current_finger`
3. Click 4 times on image → `mousePressEvent()` converts coords → append to `selected_points`
4. Real-time measurement via `calculate_joint_distances()` if "Show Measurements" enabled
5. Save → JSON with landmarks (pixels), measurements (cm), scale info, AprilTag data

### JSON Output Format
```json
{
  "thumb_0": {"x": 100, "y": 200},  // Original image pixels
  "thumb_1": {"x": 110, "y": 190},
  ...
  "measurements": {
    "thumb": [
      {
        "from_joint": 0,
        "to_joint": 1,
        "pixel_distance": 14.14,
        "cm_distance": 2.65  // Using pixels_per_cm ratio
      }
    ]
  },
  "scale_info": {
    "calibrated": true,
    "pixels_per_cm": 5.3425
  },
  "apriltags": [{"id": 11, "corners": [...]}]
}
```

## Measurement System

### Calibration
- AprilTag is exactly 7×7 cm
- Detect tag corners in image (pixels)
- `pixels_per_cm = avg_edge_length / 7.0`
- This ratio calibrates the image

### Measurement
- Calculate pixel distance between any two joints: `√((x2-x1)² + (y2-y1)²)`
- Convert to cm: `cm_distance = pixel_distance / pixels_per_cm`
- **Accuracy:** ±0.2-0.3 cm typical (varies with AprilTag detection quality)

### Validation
- Measurements should match typical hand proportions (see MEASUREMENT_QUICKREF.md)
- Check `scale_info.pixels_per_cm` to verify calibration quality
- Run multiple images of same hand for consistency checks

## GUI Layout (Enhanced Version)

**Three panels:**
- **Left (20%):** Controls (load image, finger selection, buttons)
- **Center (60%):** Image canvas with click detection
- **Right (20%):** Two-tab data display
  - Tab 1 (Landmarks): Joint coordinates in pixels
  - Tab 2 (Measurements): Distance values in cm
  - Both expand to fill available height (important for visibility)

## Important Implementation Details

### AprilTag Detection
- Uses OpenCV's ArUco module with `DICT_APRILTAG_36h11`
- Supports tags 0-587
- Returns corners as 4 × (x, y) points
- Fallback support for older OpenCV versions

### Hand Landmarks Structure
- 5 fingers (thumb, index, middle, ring, pinky)
- 4 points per finger (Start, Joint1, Joint2, End)
- Stored as `{finger}_{point_index}` format
- All coordinates are in original image pixel space

### Color Coding (Consistent Across Tools)
- Thumb: Blue (255, 0, 0 BGR)
- Index: Green (0, 255, 0)
- Middle: Red (0, 0, 255)
- Ring: Cyan (255, 255, 0)
- Pinky: Magenta (255, 0, 255)

## Dependencies & Versions

```
opencv-python>=4.7.0     # ArUco/AprilTag, image I/O
mediapipe>=0.10.0        # Hand detection (auto mode)
PySide6>=6.5.0           # GUI framework
numpy>=1.21.0            # Numerical operations
matplotlib>=3.5.0        # Plotting (auto detection)
apriltag>=0.2.0          # AprilTag detection (alternative)
```

Note: The enhanced annotation tool (`hand_annotation_with_measurements.py`) requires PySide6. Basic tools work without it.

## Key Files

| File | Purpose | Entry Point |
|------|---------|-------------|
| `hand_annotation_with_measurements.py` | Enhanced GUI with measurements | `main()` |
| `hand_annotation_gui.py` | Basic annotation GUI | `main()` |
| `hand_pose_apriltag_detector.py` | Batch auto-detection | `main()` |
| `analyze_measurements.py` | Analysis tool for multiple files | `main()` |
| `view_landmarks.py` | Visualization viewer | `main()` with arg |
| `convert_landmarks.py` | Format converter | `main()` with arg |

## Common Issues & Solutions

**"Scale Calibrated" shows "No scale" (gray)**
- Image must contain AprilTag marker
- AprilTag must be clearly visible and not rotated
- Check image format and quality

**Measurements seem incorrect**
- Verify AprilTag is perpendicular to camera
- Re-annotate joints with more precision
- Compare with reference measurements (see MEASUREMENT_QUICKREF.md)

**GUI appears crowded/text cut off**
- Right panel now expands with stretch factors
- Scroll areas are responsive to window resizing
- Window minimum size: 1500×950

**Import errors**
- Ensure all dependencies installed: `pip install -r requirements.txt`
- Verify correct Python environment (conda: `tpy11`)
- For PySide6 issues: `pip install --upgrade PySide6`

## Development Notes

### When Modifying GUI
- Keep coordinate conversion in `mousePressEvent()` - this is critical
- Scale factors must reference original image dimensions, not display dimensions
- Color assignments are consistent across all files - update all if changing

### When Adding Features
- Always validate against original image pixels, not widget coordinates
- Measurements assume planar hand projection - 3D considerations would be major change
- AprilTag calibration happens once per image load

### Testing Annotations
- Test with images that have AprilTag in different positions
- Verify pixel-to-cm conversion against known measurements
- Check that zoom level doesn't affect stored coordinates

## Performance Characteristics

- **Calibration:** Instant per image
- **Annotation:** 2-5 minutes per hand (operator-dependent)
- **Batch analysis:** Processes 100 images in ~10 seconds
- **Memory:** ~100-200 MB typical usage

## Future Considerations

- Multi-hand support would require UI redesign
- 3D pose estimation requires depth calibration
- Real-time video stream support needs performance optimization
- Database backend for large annotation sets
