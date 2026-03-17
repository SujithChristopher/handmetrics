"""
test_measurement.py — Unit tests for the homography-based MeasurementCalculator.

Run with: uv run pytest test_measurement.py -v
"""

import sys
import os
import numpy as np
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))
from core.measurement import MeasurementCalculator


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_fronto_parallel_corners(tag_size_px: float = 100.0, origin_x: float = 50.0, origin_y: float = 50.0) -> np.ndarray:
    """
    Return 4 corners of a perfect axis-aligned square in pixel space.
    Order: TL, TR, BR, BL (same as OpenCV ArUco output).
    """
    return np.array([
        [origin_x,              origin_y],               # TL
        [origin_x + tag_size_px, origin_y],              # TR
        [origin_x + tag_size_px, origin_y + tag_size_px],# BR
        [origin_x,              origin_y + tag_size_px], # BL
    ], dtype=np.float32)


def make_trapezoid_corners(tag_size_px: float = 100.0, skew: float = 20.0) -> np.ndarray:
    """
    Simulate a perspective-distorted tag (camera tilted sideways).
    The right edge is compressed by `skew` pixels to mimic tilt foreshortening.
    """
    return np.array([
        [0.0,                  0.0],                     # TL
        [tag_size_px,          0.0],                     # TR
        [tag_size_px - skew,   tag_size_px - skew],      # BR (foreshortened)
        [skew,                 tag_size_px - skew],      # BL (foreshortened)
    ], dtype=np.float32)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestMeasurementCalculatorInit:
    def test_not_calibrated_on_init(self):
        calc = MeasurementCalculator()
        assert not calc.scale_calibrated
        assert calc.homography is None
        assert calc.pixels_per_cm is None

    def test_default_tag_size(self):
        calc = MeasurementCalculator()
        assert calc.apriltag_size_cm == pytest.approx(7.0)
        assert calc.apriltag_size_m == pytest.approx(0.07)


class TestCalibrateFromApriltag:
    def test_successful_calibration(self):
        calc = MeasurementCalculator()
        corners = make_fronto_parallel_corners(tag_size_px=70.0)
        result = calc.calibrate_from_apriltag(corners)
        assert result is True
        assert calc.scale_calibrated
        assert calc.homography is not None
        assert calc.pixels_per_cm is not None

    def test_invalid_corners_returns_false(self):
        calc = MeasurementCalculator()
        assert calc.calibrate_from_apriltag(None) is False
        assert calc.calibrate_from_apriltag(np.zeros((3, 2))) is False  # only 3 pts

    def test_pixels_per_cm_approx_display_hint(self):
        """pixels_per_cm is a display-only approximation, not used for actual distance."""
        calc = MeasurementCalculator()
        # 70px tag → 7cm, so approx ratio = 70/7 = 10
        corners = make_fronto_parallel_corners(tag_size_px=70.0)
        calc.calibrate_from_apriltag(corners)
        assert calc.pixels_per_cm == pytest.approx(10.0, abs=0.5)


class TestPixelPointToCm:
    def test_fronto_parallel_origin_maps_to_zero(self):
        """TL corner of the tag should map to (0, 0) cm."""
        calc = MeasurementCalculator()
        corners = make_fronto_parallel_corners(tag_size_px=100.0, origin_x=0.0, origin_y=0.0)
        calc.calibrate_from_apriltag(corners)
        x_cm, y_cm = calc.pixel_point_to_cm(0.0, 0.0)
        assert x_cm == pytest.approx(0.0, abs=0.01)
        assert y_cm == pytest.approx(0.0, abs=0.01)

    def test_fronto_parallel_br_maps_to_tag_size(self):
        """BR corner of a 100px tag (7cm) should map to (7, 7) cm."""
        calc = MeasurementCalculator()
        corners = make_fronto_parallel_corners(tag_size_px=100.0, origin_x=0.0, origin_y=0.0)
        calc.calibrate_from_apriltag(corners)
        x_cm, y_cm = calc.pixel_point_to_cm(100.0, 100.0)
        assert x_cm == pytest.approx(7.0, abs=0.05)
        assert y_cm == pytest.approx(7.0, abs=0.05)

    def test_raises_if_not_calibrated(self):
        calc = MeasurementCalculator()
        with pytest.raises(RuntimeError):
            calc.pixel_point_to_cm(10.0, 10.0)


class TestPixelDistanceToCm:
    def test_fronto_parallel_horizontal_distance(self):
        """
        With a 100px-per-7cm tag, a horizontal span of 100px inside the tag
        should measure approximately 7 cm.
        """
        calc = MeasurementCalculator()
        corners = make_fronto_parallel_corners(tag_size_px=100.0, origin_x=0.0, origin_y=0.0)
        calc.calibrate_from_apriltag(corners)
        # The full width of the tag in pixels → should be 7 cm
        dist = calc.pixel_distance_to_cm(0.0, 0.0, 100.0, 0.0)
        assert dist == pytest.approx(7.0, abs=0.1)

    def test_fronto_parallel_diagonal_distance(self):
        """Diagonal of a 7×7 cm square = 7√2 ≈ 9.899 cm."""
        calc = MeasurementCalculator()
        corners = make_fronto_parallel_corners(tag_size_px=100.0, origin_x=0.0, origin_y=0.0)
        calc.calibrate_from_apriltag(corners)
        dist = calc.pixel_distance_to_cm(0.0, 0.0, 100.0, 100.0)
        assert dist == pytest.approx(7.0 * np.sqrt(2), abs=0.2)

    def test_uncalibrated_returns_zero(self):
        calc = MeasurementCalculator()
        assert calc.pixel_distance_to_cm(0, 0, 100, 100) == pytest.approx(0.0)

    def test_perspective_distorted_tag_still_measures_correctly(self):
        """
        Even with a trapezoidal (perspective-distorted) tag, the TL→TR pixel
        distance in the physical world should still be 7 cm.
        """
        calc = MeasurementCalculator()
        corners = make_trapezoid_corners(tag_size_px=100.0, skew=20.0)
        calc.calibrate_from_apriltag(corners)
        # TL = (0,0), TR = (100,0) in the trapezoidal view
        dist = calc.pixel_distance_to_cm(0.0, 0.0, 100.0, 0.0)
        # Due to projective correction the real-world top edge is 7 cm
        assert dist == pytest.approx(7.0, abs=0.3)


class TestSetApriltagSize:
    def test_recalculates_after_size_change(self):
        calc = MeasurementCalculator()
        corners = make_fronto_parallel_corners(tag_size_px=100.0, origin_x=0.0, origin_y=0.0)
        calc.calibrate_from_apriltag(corners)

        # Change tag size to 5 cm
        result = calc.set_apriltag_size(0.05)
        assert result is True
        assert calc.apriltag_size_cm == pytest.approx(5.0)
        # The homography should have been recomputed (not None)
        assert calc.homography is not None

    def test_invalid_size_returns_false(self):
        calc = MeasurementCalculator()
        assert calc.set_apriltag_size(-1.0) is False
        assert calc.set_apriltag_size(0.0) is False

    def test_size_change_without_prior_calibration(self):
        """If tag size changes before calibration, returns False (no corners yet)."""
        calc = MeasurementCalculator()
        result = calc.set_apriltag_size(0.05)
        assert result is False  # no raw corners stored yet


class TestGetScaleInfo:
    def test_calibrated_info(self):
        calc = MeasurementCalculator()
        corners = make_fronto_parallel_corners(tag_size_px=70.0)
        calc.calibrate_from_apriltag(corners)
        info = calc.get_scale_info()
        assert info['calibrated'] is True
        assert info['homography_available'] is True
        assert info['pixels_per_cm'] is not None
        assert info['apriltag_size_cm'] == pytest.approx(7.0)

    def test_uncalibrated_info(self):
        calc = MeasurementCalculator()
        info = calc.get_scale_info()
        assert info['calibrated'] is False
        assert info['homography_available'] is False


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
