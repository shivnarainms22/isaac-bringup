"""Host-side tests for ground-camera geometry (no Isaac needed)."""
import math

import pytest

from isaac.static_cam import (
    DEFAULT_STATIC_CAM,
    NOMINAL_DRONE_HOVER,
    elevation_deg,
    ground_range_m,
)


def test_level_target_is_zero_elevation():
    assert elevation_deg((0.0, 0.0, 1.0), (5.0, 0.0, 1.0)) == pytest.approx(0.0)


def test_straight_up_is_ninety_degrees():
    assert elevation_deg((0.0, 0.0, 0.0), (0.0, 0.0, 3.0)) == pytest.approx(90.0)


def test_forty_five_degrees_when_rise_equals_run():
    # 3 m up, 3 m across -> 45 degrees.
    assert elevation_deg((0.0, 0.0, 0.0), (3.0, 0.0, 3.0)) == pytest.approx(45.0)


def test_elevation_uses_horizontal_distance_across_both_axes():
    # target 3 m in x and 4 m in y -> 5 m horizontal; 5 m up -> 45 degrees.
    assert elevation_deg((0.0, 0.0, 0.0), (3.0, 4.0, 5.0)) == pytest.approx(45.0)


def test_default_camera_points_up_at_the_hover_point():
    # The default placement should require an upward (positive) look angle.
    elev = elevation_deg(DEFAULT_STATIC_CAM.translate, NOMINAL_DRONE_HOVER)
    assert elev > 0.0


def test_ground_range_is_euclidean():
    assert ground_range_m((0.0, 0.0, 0.0), (3.0, 4.0, 0.0)) == pytest.approx(5.0)
    assert ground_range_m((0.0, 0.0, 0.0), (0.0, 0.0, 2.0)) == pytest.approx(2.0)


def test_non_finite_positions_rejected():
    with pytest.raises(ValueError):
        elevation_deg((0.0, 0.0, math.inf), (1.0, 1.0, 1.0))
