import math

import pytest

from isaac.camera_config import CameraMount, to_usd_transform


def test_forward_facing_default_mount_translates_forward_and_no_rotation():
    mount = CameraMount(forward_m=0.12, right_m=0.0, up_m=0.02,
                        pitch_deg=0.0, yaw_deg=0.0, roll_deg=0.0)
    t = to_usd_transform(mount)
    # Body frame: +X forward, +Y right, +Z up.
    assert t.translate == (0.12, 0.0, 0.02)
    assert t.orient_euler_deg == (0.0, 0.0, 0.0)


def test_downward_pitch_is_carried_through():
    mount = CameraMount(forward_m=0.10, right_m=0.0, up_m=0.0,
                        pitch_deg=-30.0, yaw_deg=0.0, roll_deg=0.0)
    t = to_usd_transform(mount)
    assert t.translate == (0.10, 0.0, 0.0)
    assert t.orient_euler_deg == (-30.0, 0.0, 0.0)


def test_offsets_must_be_finite():
    with pytest.raises(ValueError):
        to_usd_transform(CameraMount(forward_m=float("nan"), right_m=0.0, up_m=0.0,
                                     pitch_deg=0.0, yaw_deg=0.0, roll_deg=0.0))


def test_orient_must_be_finite():
    with pytest.raises(ValueError):
        to_usd_transform(CameraMount(forward_m=0.1, right_m=0.0, up_m=0.0,
                                     pitch_deg=math.inf, yaw_deg=0.0, roll_deg=0.0))
