import cv2
import mediapipe as mp
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Rectangle
import matplotlib.patches as mpatches

try:
    import apriltag
    APRILTAG_AVAILABLE = True
except ImportError:
    APRILTAG_AVAILABLE = False
    print("Warning: apriltag not installed. AprilTag detection will be skipped.")
    print("Install it with: pip install apriltag")


class HandPoseAndAprilTagDetector:
    def __init__(self):
        """Initialize MediaPipe hand detector and AprilTag detector."""
        # Initialize MediaPipe Hand Detection
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=True,
            max_num_hands=2,
            min_detection_confidence=0.5
        )

        # Initialize AprilTag detector if available
        if APRILTAG_AVAILABLE:
            self.apriltag_detector = apriltag.Detector(
                families='tag36h11',
                nthreads=1,
                quad_decimate=1.0,
                quad_blur=0.0,
                refine_edges=1,
                decode_sharpening=0.25,
                debug=0
            )
        else:
            self.apriltag_detector = None

    def detect_hand_pose(self, image):
        """Detect hand pose in the image using MediaPipe."""
        h, w, c = image.shape
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        results = self.hands.process(image_rgb)

        hands_data = []
        if results.multi_hand_landmarks:
            for hand_landmarks, handedness in zip(
                results.multi_hand_landmarks,
                results.multi_handedness
            ):
                hand_info = {
                    'landmarks': hand_landmarks,
                    'handedness': handedness.classification[0].label,
                    'confidence': handedness.classification[0].score
                }
                hands_data.append(hand_info)

        return hands_data, results

    def detect_apriltags(self, image):
        """Detect AprilTag markers in the image using OpenCV-compatible detection."""
        if not APRILTAG_AVAILABLE or self.apriltag_detector is None:
            return []

        # Convert to grayscale for AprilTag detection
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Detect AprilTags
        tags = self.apriltag_detector.detect(gray)

        return tags

    def process_image(self, image_path):
        """Process a single image and detect hand pose and AprilTags."""
        print(f"\nProcessing: {image_path}")

        # Read image
        image = cv2.imread(str(image_path))
        if image is None:
            print(f"Error: Could not read image {image_path}")
            return None

        original_image = image.copy()
        h, w = image.shape[:2]
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        print(f"Image size: {w}x{h}")

        # Detect hand pose
        print("Detecting hand pose...")
        hand_data, _ = self.detect_hand_pose(image)
        print(f"Detected {len(hand_data)} hand(s)")
        if hand_data:
            for i, hand in enumerate(hand_data):
                print(f"  Hand {i+1}: {hand['handedness']} (confidence: {hand['confidence']:.3f})")

        # Detect AprilTags
        print("Detecting AprilTags...")
        tags = self.detect_apriltags(original_image)
        print(f"Detected {len(tags)} AprilTag(s)")
        if tags:
            for tag in tags:
                print(f"  Tag ID: {tag.tag_id}, Hamming: {tag.hamming}, Decision margin: {tag.decision_margin:.3f}")

        return image_rgb, hand_data, tags

    def create_visualization(self, image_rgb, hand_data, tags, filename):
        """Create and save a matplotlib figure with detected hand and AprilTag."""
        fig, ax = plt.subplots(1, 1, figsize=(12, 9))

        h, w = image_rgb.shape[:2]
        ax.imshow(image_rgb)
        ax.set_title(f"Detection Results - {filename}", fontsize=14, fontweight='bold')

        # Draw hand landmarks and skeleton
        if hand_data:
            colors = ['red', 'blue']  # Different colors for different hands

            for hand_idx, hand_info in enumerate(hand_data):
                landmarks = hand_info['landmarks']
                handedness = hand_info['handedness']
                confidence = hand_info['confidence']
                color = colors[hand_idx % len(colors)]

                # Hand skeleton connections
                connections = [
                    (0, 1), (1, 2), (2, 3), (3, 4),      # Thumb
                    (0, 5), (5, 6), (6, 7), (7, 8),      # Index
                    (0, 9), (9, 10), (10, 11), (11, 12), # Middle
                    (0, 13), (13, 14), (14, 15), (15, 16), # Ring
                    (0, 17), (17, 18), (18, 19), (19, 20), # Pinky
                    (5, 9), (9, 13), (13, 17)             # Palm connections
                ]

                # Draw connections
                for start, end in connections:
                    start_point = landmarks.landmark[start]
                    end_point = landmarks.landmark[end]
                    x1, y1 = int(start_point.x * w), int(start_point.y * h)
                    x2, y2 = int(end_point.x * w), int(end_point.y * h)
                    ax.plot([x1, x2], [y1, y2], color=color, linewidth=2, alpha=0.7)

                # Draw landmarks
                for idx, landmark in enumerate(landmarks.landmark):
                    x = int(landmark.x * w)
                    y = int(landmark.y * h)
                    ax.scatter(x, y, c=color, s=40, alpha=0.8, marker='o', edgecolors='white', linewidth=0.5)

                # Add hand label
                first_landmark = landmarks.landmark[0]
                label_x = int(first_landmark.x * w)
                label_y = int(first_landmark.y * h) - 20
                ax.text(label_x, label_y, f"{handedness} ({confidence:.2f})",
                       fontsize=10, color=color, fontweight='bold',
                       bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

        # Draw AprilTags
        if tags:
            for tag in tags:
                corners = tag.corners

                # Draw tag boundary
                rect = Polygon(corners, fill=False, edgecolor='lime', linewidth=2)
                ax.add_patch(rect)

                # Calculate center and draw tag info
                center = corners.mean(axis=0)
                ax.text(int(center[0]), int(center[1]), f"ID: {tag.tag_id}\nHamming: {tag.hamming}",
                       fontsize=10, color='lime', fontweight='bold',
                       bbox=dict(boxstyle='round', facecolor='black', alpha=0.7),
                       ha='center', va='center')

        ax.axis('off')
        plt.tight_layout()

        return fig

    def process_folder(self, folder_path, plots_folder="plots"):
        """Process all images in a folder and save plots."""
        folder = Path(folder_path)

        if not folder.exists():
            print(f"Error: Folder {folder_path} does not exist")
            return

        # Create plots folder
        plots_path = Path(plots_folder)
        plots_path.mkdir(parents=True, exist_ok=True)

        # Supported image extensions
        image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff'}

        # Process all images
        image_files = [f for f in folder.iterdir()
                      if f.suffix.lower() in image_extensions]

        if not image_files:
            print(f"No images found in {folder_path}")
            return

        print(f"Found {len(image_files)} image(s) in {folder_path}")
        print("=" * 60)

        results = []
        for image_file in image_files:
            result = self.process_image(image_file)
            if result:
                image_rgb, hand_data, tags = result
                results.append({
                    'filename': image_file.name,
                    'image': image_rgb,
                    'hands': hand_data,
                    'tags': tags
                })

                # Create and save visualization
                fig = self.create_visualization(image_rgb, hand_data, tags, image_file.name)
                output_file = plots_path / f"detected_{image_file.stem}.png"
                fig.savefig(str(output_file), dpi=150, bbox_inches='tight')
                plt.close(fig)
                print(f"Saved plot: {output_file}")

        print("=" * 60)
        return results


def main():
    """Main function."""
    # Create detector
    detector = HandPoseAndAprilTagDetector()

    # Process images folder
    images_folder = "images"
    plots_folder = "plots"

    results = detector.process_folder(images_folder, plots_folder)

    if results:
        print(f"\nProcessed {len(results)} image(s) successfully!")
        print(f"All plots saved to '{plots_folder}' folder")
    else:
        print("No images processed")


if __name__ == "__main__":
    main()
