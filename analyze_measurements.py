"""
Analyze hand joint measurements from multiple annotated images.
"""

import json
import statistics
from pathlib import Path
from typing import Dict, List
import sys


class MeasurementAnalyzer:
    """Analyze and compare hand measurements."""

    def __init__(self):
        self.all_measurements = []
        self.finger_names = ['thumb', 'index', 'middle', 'ring', 'pinky']

    def load_measurements_file(self, json_path: str) -> Dict:
        """Load measurements from a JSON file."""
        with open(json_path, 'r') as f:
            return json.load(f)

    def add_file(self, json_path: str):
        """Add measurements from a file."""
        try:
            data = self.load_measurements_file(json_path)

            if 'measurements' not in data:
                print(f"⚠️  No measurements in {json_path}")
                return

            entry = {
                'file': str(json_path),
                'image_path': data.get('image_path', 'Unknown'),
                'measurements': data['measurements'],
                'scale_info': data.get('scale_info', {})
            }
            self.all_measurements.append(entry)
            print(f"✓ Loaded: {json_path}")

        except Exception as e:
            print(f"✗ Error loading {json_path}: {e}")

    def get_finger_segments(self, finger: str) -> Dict[str, List[float]]:
        """Get all segment measurements for a specific finger."""
        segments = {
            'segment_0_1': [],  # Base to Joint1
            'segment_1_2': [],  # Joint1 to Joint2
            'segment_2_3': []   # Joint2 to Tip
        }

        for entry in self.all_measurements:
            if finger in entry['measurements']:
                for dist_info in entry['measurements'][finger]:
                    from_j = dist_info['from_joint']
                    to_j = dist_info['to_joint']
                    cm_distance = dist_info['cm_distance']

                    key = f'segment_{from_j}_{to_j}'
                    if key in segments:
                        segments[key].append(cm_distance)

        return segments

    def calculate_statistics(self) -> Dict:
        """Calculate statistics for all fingers and segments."""
        stats = {}

        for finger in self.finger_names:
            segments = self.get_finger_segments(finger)
            finger_stats = {}

            for segment_name, distances in segments.items():
                if distances:
                    finger_stats[segment_name] = {
                        'count': len(distances),
                        'mean': statistics.mean(distances),
                        'median': statistics.median(distances),
                        'std_dev': statistics.stdev(distances) if len(distances) > 1 else 0.0,
                        'min': min(distances),
                        'max': max(distances),
                        'range': max(distances) - min(distances),
                        'all_values': distances
                    }

            stats[finger] = finger_stats

        return stats

    def print_summary(self):
        """Print a summary of all measurements."""
        print("\n" + "=" * 80)
        print("HAND JOINT MEASUREMENT ANALYSIS SUMMARY")
        print("=" * 80)

        print(f"\nFiles Analyzed: {len(self.all_measurements)}")
        for entry in self.all_measurements:
            print(f"  • {entry['file']}")
            if entry['scale_info'].get('calibrated'):
                print(f"    Scale: {entry['scale_info'].get('pixels_per_cm', 'N/A'):.4f} pixels/cm")

    def print_statistics(self):
        """Print detailed statistics."""
        stats = self.calculate_statistics()

        print("\n" + "=" * 80)
        print("DETAILED STATISTICS")
        print("=" * 80)

        segment_labels = {
            'segment_0_1': 'Base → Joint1 (Metacarpal to PIP)',
            'segment_1_2': 'Joint1 → Joint2 (PIP to DIP)',
            'segment_2_3': 'Joint2 → Tip (DIP to Fingertip)'
        }

        for finger in self.finger_names:
            print(f"\n{'='*80}")
            print(f"{finger.upper().ljust(10)} Segment Measurements")
            print(f"{'='*80}")

            if finger not in stats or not stats[finger]:
                print(f"  No measurements available")
                continue

            for segment_name, segment_stats in sorted(stats[finger].items()):
                label = segment_labels.get(segment_name, segment_name)
                print(f"\n  {label}")
                print(f"    Count:      {segment_stats['count']} measurements")
                print(f"    Mean:       {segment_stats['mean']:.3f} cm")
                print(f"    Median:     {segment_stats['median']:.3f} cm")
                print(f"    Std Dev:    ±{segment_stats['std_dev']:.3f} cm")
                print(f"    Min:        {segment_stats['min']:.3f} cm")
                print(f"    Max:        {segment_stats['max']:.3f} cm")
                print(f"    Range:      {segment_stats['range']:.3f} cm")

    def print_totals(self):
        """Print total finger length statistics."""
        print("\n" + "=" * 80)
        print("TOTAL FINGER LENGTHS")
        print("=" * 80)

        for finger in self.finger_names:
            print(f"\n{finger.upper()}")

            total_lengths = []

            for entry in self.all_measurements:
                if finger in entry['measurements']:
                    total = sum(dist['cm_distance'] for dist in entry['measurements'][finger])
                    total_lengths.append(total)

            if total_lengths:
                print(f"  Count:      {len(total_lengths)} measurements")
                print(f"  Mean:       {statistics.mean(total_lengths):.3f} cm")
                print(f"  Median:     {statistics.median(total_lengths):.3f} cm")
                if len(total_lengths) > 1:
                    print(f"  Std Dev:    ±{statistics.stdev(total_lengths):.3f} cm")
                print(f"  Min:        {min(total_lengths):.3f} cm")
                print(f"  Max:        {max(total_lengths):.3f} cm")
            else:
                print(f"  No measurements available")

    def print_comparison_table(self):
        """Print comparison table for all fingers."""
        print("\n" + "=" * 80)
        print("COMPARISON TABLE - Mean Measurements (cm)")
        print("=" * 80)

        stats = self.calculate_statistics()

        # Header
        print(f"\n{'Segment':<20}", end="")
        for finger in self.finger_names:
            print(f"{finger.capitalize():<15}", end="")
        print()
        print("-" * 100)

        # Rows
        for segment_key in ['segment_0_1', 'segment_1_2', 'segment_2_3']:
            segment_label = {
                'segment_0_1': 'Base → Joint1',
                'segment_1_2': 'Joint1 → Joint2',
                'segment_2_3': 'Joint2 → Tip'
            }[segment_key]

            print(f"{segment_label:<20}", end="")

            for finger in self.finger_names:
                if finger in stats and segment_key in stats[finger]:
                    mean_val = stats[finger][segment_key]['mean']
                    std_val = stats[finger][segment_key]['std_dev']
                    print(f"{mean_val:.2f}±{std_val:.2f}".ljust(15), end="")
                else:
                    print("N/A".ljust(15), end="")

            print()

    def export_csv(self, output_file: str):
        """Export measurements to CSV file."""
        try:
            import csv

            stats = self.calculate_statistics()

            with open(output_file, 'w', newline='') as f:
                writer = csv.writer(f)

                # Header
                writer.writerow(['Finger', 'Segment', 'Count', 'Mean (cm)', 'Median (cm)',
                               'Std Dev', 'Min (cm)', 'Max (cm)', 'Range (cm)'])

                # Data
                for finger in self.finger_names:
                    if finger in stats:
                        for segment_name, segment_stats in sorted(stats[finger].items()):
                            writer.writerow([
                                finger,
                                segment_name,
                                segment_stats['count'],
                                f"{segment_stats['mean']:.3f}",
                                f"{segment_stats['median']:.3f}",
                                f"{segment_stats['std_dev']:.3f}",
                                f"{segment_stats['min']:.3f}",
                                f"{segment_stats['max']:.3f}",
                                f"{segment_stats['range']:.3f}"
                            ])

            print(f"\n✓ CSV exported to: {output_file}")

        except ImportError:
            print("CSV module not available")
        except Exception as e:
            print(f"Error exporting CSV: {e}")

    def export_json_summary(self, output_file: str):
        """Export analysis summary to JSON."""
        try:
            stats = self.calculate_statistics()

            # Remove 'all_values' from stats for cleaner JSON
            clean_stats = {}
            for finger, finger_stats in stats.items():
                clean_stats[finger] = {}
                for segment, segment_data in finger_stats.items():
                    clean_stats[finger][segment] = {
                        'count': segment_data['count'],
                        'mean': round(segment_data['mean'], 3),
                        'median': round(segment_data['median'], 3),
                        'std_dev': round(segment_data['std_dev'], 3),
                        'min': round(segment_data['min'], 3),
                        'max': round(segment_data['max'], 3),
                        'range': round(segment_data['range'], 3)
                    }

            output = {
                'summary': {
                    'files_analyzed': len(self.all_measurements),
                    'file_list': [entry['file'] for entry in self.all_measurements]
                },
                'statistics': clean_stats
            }

            with open(output_file, 'w') as f:
                json.dump(output, f, indent=2)

            print(f"✓ JSON summary exported to: {output_file}")

        except Exception as e:
            print(f"Error exporting JSON: {e}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python analyze_measurements.py <json_file1> [json_file2] [json_file3] ...")
        print("\nExample:")
        print("  python analyze_measurements.py hand1.json hand2.json hand3.json")
        print("\nThe script will analyze and compare measurements from multiple annotated images.")
        sys.exit(1)

    json_files = sys.argv[1:]

    analyzer = MeasurementAnalyzer()

    print("\n" + "=" * 80)
    print("LOADING MEASUREMENT FILES")
    print("=" * 80 + "\n")

    for json_file in json_files:
        analyzer.add_file(json_file)

    if not analyzer.all_measurements:
        print("\n✗ No valid measurement files loaded")
        sys.exit(1)

    # Print analysis
    analyzer.print_summary()
    analyzer.print_statistics()
    analyzer.print_totals()
    analyzer.print_comparison_table()

    # Export results
    print("\n" + "=" * 80)
    print("EXPORTING RESULTS")
    print("=" * 80)

    csv_file = "hand_measurements_analysis.csv"
    json_file = "hand_measurements_summary.json"

    analyzer.export_csv(csv_file)
    analyzer.export_json_summary(json_file)

    print("\n" + "=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)
    print("\nGenerated files:")
    print(f"  • {csv_file}")
    print(f"  • {json_file}")
    print()


if __name__ == "__main__":
    main()
