# Crease-Based Annotation & Geometric Analysis System

## 🚀 Overview

This update shifts the paradigm from **Finger-Based Annotation** to **Crease-Based Annotation**. Instead of tracing individual fingers, we now trace specific creases across the hand (Crease 1, Crease 2, Crease 3). This approach is optimized for analyzing the geometric relationship between creases, providing a CAD-style engineering analysis of the hand's structure.

## ✨ Key Features

### 1. Crease-Based Annotation
*   **3 Creases**: Annotation is organized by "Crease 1", "Crease 2", and "Crease 3".
*   **Variable Points**: No fixed limit on points. You can add as many points as needed to define the crease segments.
*   **Sequential Pair Measurement**:
    *   **Segment**: A pair of points (p0→p1, p2→p3, p4→p5, etc.) defines a "crease segment".
    *   **Gap Handling**: The system automatically skips the "gaps" between segments (e.g., p1→p2 is ignored).
    *   **Measurement**: Only the actual segments are measured and visualized.

### 2. Dual-View Interface
*   **🖼️ Image View**: 
    *   Standard annotation interface.
    *   Click to add points along creases.
    *   AprilTag detection for automatic scale calibration.
    *   Real-time segment length display.
*   **📊 Plot View (New!)**:
    *   Full-screen CAD-style engineering diagram.
    *   **Black Background**: High-contrast professional visualization.
    *   **Real Units**: All axes and measurements in **centimeters (cm)**.
    *   **Inverted Y-Axis**: Matches image coordinate system.

### 3. Geometric Analysis (CAD Plot)
The "Geometric Plot" provides a sophisticated structural analysis of the first 3 segments (Index, Middle, Ring) of Crease 1 and Crease 2:

*   **Color Coding**:
    *   **Cyan**: Crease 1 segments and centers.
    *   **Yellow**: Crease 2 segments and centers.
    *   **Magenta**: Cross-crease connections.
    *   **Green**: Grid, axes, and text (Classic CAD style).

*   **Visualization Elements**:
    *   **Segments**: Solid lines representing the annotated crease segments.
    *   **Centers**: Square markers indicating the geometric center of each segment.
    *   **Centerlines**: Dashed lines connecting the centers of segments within the same crease.
    *   **Cross-Connections**: Dotted magenta lines connecting corresponding segments between Crease 1 and Crease 2 (e.g., Index C1 ↔ Index C2).

*   **Comprehensive Measurements**:
    1.  **Along-Crease**: Distance between neighboring segment centers (e.g., Index Center → Middle Center).
    2.  **Cross-Crease**: Distance between corresponding segments on different creases (e.g., C1 Index → C2 Index).
    3.  **Segment Lengths**: Length of each individual crease segment.

## 🛠️ Implementation Details (`main.py`)

### Modified Data Structure
The `ImageCanvas` class now organizes data by crease rather than finger:
```python
self.selected_points = {
    'crease1': [], # List of (x,y) tuples
    'crease2': [],
    'crease3': []
}
```

### Measurement Logic
The `calculate_joint_distances` method uses a step-2 iterator to measure distinct segments:
```python
# Measure pairs: (0,1), (2,3), (4,5)...
for i in range(0, len(points) - 1, 2):
    p1 = points[i]
    p2 = points[i+1]
    # Calculate distance...
```

### Geometric Plotting
The `update_geometric_plot` method performs the heavy lifting for the CAD view:
1.  **Extract Segments**: Takes the first 6 points (3 pairs) from Crease 1 and Crease 2.
2.  **Calculate Centers**: Computes midpoint `(p_start + p_end) / 2` for each segment.
3.  **Unit Conversion**: Converts all pixel coordinates to centimeters using the AprilTag scale factor.
4.  **Rendering**: Uses `matplotlib` with a custom dark theme to render the engineering diagram.

## 📊 JSON Output Format

The `save_landmarks` function produces a structure optimized for ML training on crease data:

```json
{
  "crease1_0": {"x": 100, "y": 200},
  "crease1_1": {"x": 150, "y": 205},
  ...
  "measurements": {
    "crease1": [
      {
        "from_point": 0,
        "to_point": 1,
        "pixel_distance": 50.5,
        "cm_distance": 2.45
      },
      ...
    ]
  },
  "scale_info": {
    "pixels_per_cm": 20.5,
    "calibrated": true
  }
}
```

## 📝 Workflow

1.  **Load Image**: Open an image containing an AprilTag (7cm).
2.  **Annotate Crease 1**:
    *   Select "Crease 1".
    *   Click Start/End for Index finger segment.
    *   Click Start/End for Middle finger segment.
    *   Click Start/End for Ring finger segment.
3.  **Annotate Crease 2**:
    *   Select "Crease 2".
    *   Repeat the process (Index, Middle, Ring segments).
4.  **Analyze**:
    *   Click **"📊 Switch to Plot View"**.
    *   Examine the CAD diagram for geometric relationships.
    *   Verify distances (cm).
5.  **Export**:
    *   Click "💾 Save Landmarks" to generate the JSON dataset.
    *   Click "💾 Save Analysis (CSV)" to export geometric data (angles, distances) to CSV.
    *   Click "📄 Generate Report" for a PDF summary.

### 4. Advanced Geometric Metrics
*   **Reference Lines**: White dashed lines connecting the midpoints of the vertical segments (Index→Middle, Middle→Ring).
*   **4 Key Angles**:
    *   **Ang1**: Vertical 1 (Index) vs Line 1-2.
    *   **Ang2**: Vertical 2 (Middle) vs Line 1-2.
    *   **Ang3**: Vertical 2 (Middle) vs Line 2-3.
    *   **Ang4**: Vertical 3 (Ring) vs Line 2-3.
*   **CSV Export**: Saves these angles along with all segment lengths and cross-crease distances to a structured CSV file for analysis.
