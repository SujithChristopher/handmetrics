---
name: crease-analysis-system
description: Instructions for the Crease-Based Annotation and CAD-style Geometric Analysis system.
---

# Crease-Based Annotation & Geometric Analysis

This system shifts from finger tracing to structural crease analysis across the hand.

## 1. Annotation Strategy
- **Creases**: Organize points by "Crease 1", "Crease 2", and "Crease 3".
- **Segments**: Points are processed in pairs (p0→p1, p2→p3, etc.).
- **Gaps**: Automatically skip intervals between pairs (e.g., p1→p2).

## 2. Geometric Analysis (CAD Plot)
The fundamental analysis focused on the first 3 segments (Index, Middle, Ring) of Crease 1 and Crease 2.

- **Coordinate System**: All measurements in **centimeters (cm)**. Y-axis is inverted to match image coordinates.
- **Colors**:
  - **Cyan**: Crease 1.
  - **Yellow**: Crease 2.
  - **Magenta**: Cross-crease connections.
  - **Green**: Grid, axes, and text.
- **Elements**: Draw solid segments, square centers, dashed centerlines, and dotted cross-connections.

## 3. Key Metrics
- **Distance**: Along-crease (center to center), Cross-crease (corresponding segments), and individual segment lengths.
- **Angles**:
  - **Ang1**: Index vertical (V1) vs Ref Line 1-2.
  - **Ang2**: Middle vertical (V2) vs Reverse Ref Line 1-2.
  - **Ang3**: Middle vertical (V2) vs Ref Line 2-3.
  - **Ang4**: Ring vertical (V3) vs Reverse Ref Line 2-3.

## 4. Output Formats
- **JSON**: Landmark coordinates and scaled measurements.
- **CSV**: Geometric metrics (angles, lengths, cross-distances).
- **PDF**: Summary report with visualizations.
