# Quick Start Guide - Hand Annotation Tool

## Installation (2 minutes)

```bash
# Navigate to project directory
cd e:\NOARK_CV\hand_pose

# Install dependencies
pip install -r requirements.txt
```

## Launch the GUI (30 seconds)

```bash
python hand_annotation_gui.py
```

## Annotate a Hand (2-5 minutes per hand)

### 1. Load Image
- Click **"Load Image"** button
- Select an image from `images/` folder
- Image appears in the canvas with AprilTag detection results

### 2. Select Finger
```
Dropdown: [Thumb ▼]  ← Click to select
Options:
  • Thumb
  • Index
  • Middle
  • Ring
  • Pinky
```

### 3. Click on Image (4 times per finger)
```
Click order:
1. Start point (wrist/base of finger)
2. Joint 1 (first knuckle)
3. Joint 2 (second knuckle)
4. End point (fingertip)
```

### 4. Watch Counter Update
```
Point Counter: 0 / 4 ← Gray
Point Counter: 1 / 4 ← Gray
Point Counter: 2 / 4 ← Orange
Point Counter: 3 / 4 ← Orange
Point Counter: 4 / 4 ← Green ✓
```

### 5. Repeat for Other Fingers
- Change dropdown selection
- Click 4 times on image
- Points appear in different color

### 6. Save Landmarks
- Click **"Save Landmarks"** button
- Choose filename (e.g., `hand_landmarks.json`)
- File saved with all coordinates and AprilTag info

## View Results

```bash
# View saved landmarks
python view_landmarks.py hand_landmarks.json
```

## Correction Tips

### Made a Mistake?
```
Button: [Undo Last Point] ← Remove last click
Button: [Clear Current Finger] ← Clear selected finger
Button: [Clear All] ← Start completely over
```

### Example Workflow
```
1. Select "Index" from dropdown
2. Click 4 times on index finger
3. "Oops! Wrong position on point 2"
4. Click [Undo Last Point]
5. Click correct position for point 2
6. Select "Middle"
7. Click 4 times on middle finger
8. ...repeat for Ring and Pinky
9. Select "Thumb" last
10. Click 4 times on thumb
11. Click [Save Landmarks]
```

## Output

The script creates a JSON file like:

```json
{
  "image_path": "images/hand_photo.jpg",
  "thumb_0": {"x": 100, "y": 200},
  "thumb_1": {"x": 110, "y": 190},
  "thumb_2": {"x": 120, "y": 180},
  "thumb_3": {"x": 130, "y": 170},
  "index_0": {"x": 150, "y": 210},
  ...
  "apriltags": [{"id": 11, "corners": [...]}]
}
```

## Color Reference

When you click on the image:

- **Red/Pink points** = Thumb
- **Green points** = Index
- **Blue points** = Middle
- **Yellow/Cyan points** = Ring
- **Purple/Magenta points** = Pinky

Lines connect the points together.

## Pro Tips

✅ **Do This:**
- Use good lighting
- Make image as clear as possible
- Take time for accuracy
- Check each point visually
- Undo if unsure (no penalty)

❌ **Don't Do This:**
- Rush through annotations
- Click in vague areas
- Save before reviewing
- Annotate blurry images
- Forget to save

## Troubleshooting

### "Module not found" error
```bash
pip install -r requirements.txt --upgrade
```

### GUI window won't appear
```bash
pip install --upgrade PySide6
```

### Can't load image
- Make sure image is in `images/` folder
- Check file format (.jpg, .png, .bmp supported)
- Try double-clicking image in file explorer to verify it works

### AprilTag showing as "None"
- Don't worry, it's optional
- Proceed with finger annotation anyway

## Next Steps

After annotating:

1. **View your work:**
   ```bash
   python view_landmarks.py hand_landmarks.json
   ```

2. **Convert to MediaPipe format (optional):**
   ```bash
   python convert_landmarks.py hand_landmarks.json output.json
   ```

3. **Annotate more images:**
   - Run `python hand_annotation_gui.py` again
   - Load next image
   - Repeat workflow

## Expected Time

- **First image**: 5-10 minutes (learning curve)
- **Subsequent images**: 2-5 minutes each
- **Accuracy**: Very high (manual annotation)

## Questions?

See detailed documentation:
- [README.md](README.md) - Overview of all tools
- [README_GUI.md](README_GUI.md) - Detailed GUI documentation

---

**You're ready! Launch the GUI and start annotating:**

```bash
python hand_annotation_gui.py
```
