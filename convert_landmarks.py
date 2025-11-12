"""
Utility script to convert manually annotated hand landmarks to MediaPipe format.
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple


def load_manual_landmarks(json_path: str) -> Dict:
    """Load manually annotated landmarks from JSON."""
    with open(json_path, 'r') as f:
        return json.load(f)


def convert_to_mediapipe(manual_landmarks: Dict) -> List[Dict]:
    """
    Convert manual landmarks to MediaPipe hand landmarks format.

    MediaPipe Hand Landmarks (21 points):
    0: Wrist
    1-4: Thumb (MCP, PIP, DIP, Tip)
    5-8: Index (MCP, PIP, DIP, Tip)
    9-12: Middle (MCP, PIP, DIP, Tip)
    13-16: Ring (MCP, PIP, DIP, Tip)
    17-20: Pinky (MCP, PIP, DIP, Tip)
    """

    mediapipe_landmarks = []

    finger_mapping = {
        'thumb': (1, 4),      # indices 1-4
        'index': (5, 8),      # indices 5-8
        'middle': (9, 12),    # indices 9-12
        'ring': (13, 16),     # indices 13-16
        'pinky': (17, 20)     # indices 17-20
    }

    # Get image dimensions (estimate if not available)
    # This is used to normalize coordinates (0.0 - 1.0 range)
    image_width = 1920  # Default, can be updated
    image_height = 1080  # Default, can be updated

    # Wrist point (landmark 0) - use first point of thumb as approximation
    if 'thumb_0' in manual_landmarks:
        thumb_0 = manual_landmarks['thumb_0']
        wrist_landmark = {
            'index': 0,
            'x': thumb_0['x'] / image_width,
            'y': thumb_0['y'] / image_height,
            'z': 0.0,
            'visibility': 1.0
        }
        mediapipe_landmarks.append(wrist_landmark)

    # Add each finger's points
    for finger, (start_idx, end_idx) in finger_mapping.items():
        for joint_idx in range(start_idx, end_idx + 1):
            # Convert joint_idx to manual annotation index (0-3)
            manual_point_idx = joint_idx - start_idx
            key = f"{finger}_{manual_point_idx}"

            if key in manual_landmarks:
                point = manual_landmarks[key]
                landmark = {
                    'index': joint_idx,
                    'x': point['x'] / image_width,
                    'y': point['y'] / image_height,
                    'z': 0.0,
                    'visibility': 1.0
                }
                mediapipe_landmarks.append(landmark)

    return mediapipe_landmarks


def save_mediapipe_landmarks(landmarks: List[Dict], output_path: str):
    """Save converted landmarks to JSON in MediaPipe format."""
    output_data = {
        'format': 'mediapipe_hand_landmarks',
        'hand_landmarks': landmarks,
        'description': 'Hand landmarks in MediaPipe format (21 points)'
    }

    with open(output_path, 'w') as f:
        json.dump(output_data, f, indent=2)


def print_conversion_info(manual_landmarks: Dict, mediapipe_landmarks: List[Dict]):
    """Print information about the conversion."""
    print("\n" + "=" * 70)
    print("HAND LANDMARKS CONVERSION SUMMARY")
    print("=" * 70)

    print("\nManual Annotation Format:")
    print("  Format: {finger}_{joint_index}")
    print("  Fingers: thumb, index, middle, ring, pinky")
    print("  Joints per finger: 0 (start), 1, 2, 3 (end)")
    print(f"  Total points: {sum(1 for k in manual_landmarks if '_' in k and k not in ['image_path', 'apriltags'])}")

    print("\nMediaPipe Format:")
    print("  Landmark 0: Wrist")
    print("  Landmarks 1-4: Thumb")
    print("  Landmarks 5-8: Index")
    print("  Landmarks 9-12: Middle")
    print("  Landmarks 13-16: Ring")
    print("  Landmarks 17-20: Pinky")
    print(f"  Total landmarks: {len(mediapipe_landmarks)}")

    print("\nDetailed Mapping:")
    finger_names = ['Thumb', 'Index', 'Middle', 'Ring', 'Pinky']
    joint_names = ['Start', 'Joint1', 'Joint2', 'End']

    for finger_idx, finger_name in enumerate(finger_names):
        finger_key = ['thumb', 'index', 'middle', 'ring', 'pinky'][finger_idx]
        start_mp_idx = 1 + (finger_idx * 4)

        print(f"\n  {finger_name.upper()}:")
        for joint_idx in range(4):
            manual_key = f"{finger_key}_{joint_idx}"
            mp_idx = start_mp_idx + joint_idx

            if manual_key in manual_landmarks:
                point = manual_landmarks[manual_key]
                mp_landmark = next((l for l in mediapipe_landmarks if l['index'] == mp_idx), None)
                if mp_landmark:
                    print(f"    {joint_names[joint_idx]}: ({point['x']}, {point['y']}) -> "
                          f"MP[{mp_idx}]: ({mp_landmark['x']:.4f}, {mp_landmark['y']:.4f})")

    print("\n" + "=" * 70 + "\n")


def main():
    if len(sys.argv) < 2:
        print("Usage: python convert_landmarks.py <manual_landmarks.json> [output.json]")
        print("\nExample:")
        print("  python convert_landmarks.py hand_landmarks.json hand_landmarks_mediapipe.json")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else "hand_landmarks_mediapipe.json"

    input_path = Path(input_file)

    if not input_path.exists():
        print(f"Error: File not found: {input_file}")
        sys.exit(1)

    try:
        # Load manual landmarks
        print(f"\nLoading manual landmarks from: {input_file}")
        manual_landmarks = load_manual_landmarks(input_file)

        # Convert to MediaPipe format
        print("Converting to MediaPipe format...")
        mediapipe_landmarks = convert_to_mediapipe(manual_landmarks)

        # Save converted landmarks
        print(f"Saving to: {output_file}")
        save_mediapipe_landmarks(mediapipe_landmarks, output_file)

        # Print summary
        print_conversion_info(manual_landmarks, mediapipe_landmarks)

        print(f"✓ Conversion complete!")
        print(f"✓ Output file: {output_file}")

    except json.JSONDecodeError:
        print(f"Error: Invalid JSON file: {input_file}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
