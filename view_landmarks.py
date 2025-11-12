"""
Utility script to view and visualize saved hand landmarks.
"""

import json
import cv2
import numpy as np
from pathlib import Path
import sys


def load_landmarks(json_path):
    """Load landmarks from JSON file."""
    with open(json_path, 'r') as f:
        data = json.load(f)
    return data


def visualize_landmarks(image_path, landmarks_data):
    """Visualize landmarks on the image."""
    image = cv2.imread(str(image_path))

    if image is None:
        print(f"Error: Cannot load image {image_path}")
        return

    h, w = image.shape[:2]
    colors = {
        'thumb': (255, 0, 0),      # Blue
        'index': (0, 255, 0),      # Green
        'middle': (0, 0, 255),     # Red
        'ring': (255, 255, 0),     # Cyan
        'pinky': (255, 0, 255)     # Magenta
    }

    # Draw landmarks
    for finger in ['thumb', 'index', 'middle', 'ring', 'pinky']:
        points = []
        for i in range(4):
            key = f"{finger}_{i}"
            if key in landmarks_data:
                x, y = landmarks_data[key]['x'], landmarks_data[key]['y']
                points.append((x, y))
                cv2.circle(image, (x, y), 8, colors[finger], -1)
                cv2.putText(image, f"{i}", (x + 10, y - 10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, colors[finger], 2)

        # Draw skeleton
        if len(points) > 1:
            for i in range(len(points) - 1):
                cv2.line(image, points[i], points[i+1], colors[finger], 2)

    # Draw AprilTags if present
    if 'apriltags' in landmarks_data:
        for tag in landmarks_data['apriltags']:
            corners = np.array(tag['corners'], dtype=np.int32)
            cv2.polylines(image, [corners], True, (0, 255, 0), 2)
            center = corners.mean(axis=0).astype(int)
            cv2.putText(image, f"ID: {tag['id']}", tuple(center),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

    # Display
    cv2.imshow('Hand Landmarks', image)
    cv2.waitKey(0)
    cv2.destroyAllWindows()


def print_landmarks_info(landmarks_data):
    """Print detailed information about landmarks."""
    print("\n" + "=" * 60)
    print("HAND LANDMARKS INFORMATION")
    print("=" * 60)

    if 'image_path' in landmarks_data:
        print(f"\nImage: {landmarks_data['image_path']}")

    print("\nLandmarks:")
    fingers = ['thumb', 'index', 'middle', 'ring', 'pinky']
    point_names = ['Start', 'Joint 1', 'Joint 2', 'End']

    for finger in fingers:
        print(f"\n  {finger.upper()}:")
        for i in range(4):
            key = f"{finger}_{i}"
            if key in landmarks_data:
                x, y = landmarks_data[key]['x'], landmarks_data[key]['y']
                print(f"    {point_names[i]}: ({x}, {y})")

    if 'apriltags' in landmarks_data and landmarks_data['apriltags']:
        print(f"\nAprilTags Detected: {len(landmarks_data['apriltags'])}")
        for tag in landmarks_data['apriltags']:
            print(f"  ID: {tag['id']}, Corners: {tag['corners']}")
    else:
        print("\nAprilTags: None detected")

    print("\n" + "=" * 60 + "\n")


def main():
    if len(sys.argv) < 2:
        print("Usage: python view_landmarks.py <json_file>")
        print("\nExample: python view_landmarks.py hand_landmarks.json")
        sys.exit(1)

    json_file = sys.argv[1]
    json_path = Path(json_file)

    if not json_path.exists():
        print(f"Error: File not found: {json_file}")
        sys.exit(1)

    try:
        landmarks_data = load_landmarks(json_path)
        print_landmarks_info(landmarks_data)

        # Try to visualize if image path is available
        if 'image_path' in landmarks_data:
            image_path = landmarks_data['image_path']
            if Path(image_path).exists():
                print("Displaying image with landmarks...")
                visualize_landmarks(image_path, landmarks_data)
            else:
                print(f"Warning: Image not found at {image_path}")
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON file: {json_file}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
