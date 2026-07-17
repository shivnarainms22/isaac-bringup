"""Ground static-camera placement -> USD transform. Pure; no Isaac dependency.

The static-camera checkpoint idea puts fixed cameras on the ground that look UP/across
at the drone -- a viewpoint the drone's own (forward/down) detector never trains on. This
module holds the reproducible default placement + the geometry helper used to aim the
ground camera at the drone, so it can be unit-tested host-side (Isaac not required).

World frame convention (matches the bring-up scene): +Z = up, drone spawns near origin.
A USD Camera with identity orientation looks down world -Z (verified by the M1 overhead
cam: translate (0,0,5), euler (0,0,0) images the ground below it).
"""
from dataclasses import dataclass
from math import atan2, degrees, isfinite, sqrt


@dataclass(frozen=True)
class StaticCamPlacement:
    """Where the ground camera sits and how it is oriented, in WORLD space.

    translate: (x, y, z) world position of the camera (metres).
    orient_euler_deg: (rx, ry, rz) USD RotateXYZ Euler degrees applied to the prim.
    """
    translate: tuple
    orient_euler_deg: tuple


# Nominal point the camera is aimed at: roughly where the drone hovers after takeoff.
# (Test missions fly ~2.5-5 m up; 2.5 m is a reasonable centre of frame.)
NOMINAL_DRONE_HOVER = (0.0, 0.0, 2.5)

# Default ground camera: 5 m to the -Y side of the drone, on a ~0.5 m "tripod", pitched
# up toward the hover point. Euler is a sensible STARTING aim -- fine-tune on the box with
# verify/grab_frame.py (aiming a camera you can't preview live is an iterate-and-check loop).
DEFAULT_STATIC_CAM = StaticCamPlacement(
    translate=(0.0, -5.0, 0.5),
    orient_euler_deg=(60.0, 0.0, 0.0),
)


def elevation_deg(cam_pos, target_pos) -> float:
    """Upward angle (degrees above horizontal) from the camera to the target.

    0 = target is level with the camera; 90 = straight up. Use this as the guide for how
    far to pitch the ground camera up to frame the drone.
    """
    vals = list(cam_pos) + list(target_pos)
    if not all(isfinite(v) for v in vals):
        raise ValueError("camera/target positions must be finite")
    dx = target_pos[0] - cam_pos[0]
    dy = target_pos[1] - cam_pos[1]
    dz = target_pos[2] - cam_pos[2]
    horizontal = sqrt(dx * dx + dy * dy)
    return degrees(atan2(dz, horizontal))


def look_up_euler_deg(cam_pos, target_pos):
    """USD RotateXYZ Euler (deg) to aim a ground camera UP at a target above and ahead of it.

    Assumes the camera sits at -Y of the target and looks toward +Y (our standard placement),
    so only pitch (RX) varies. Convention (verified empirically): RX=90 is horizontal toward
    +Y, and adding the elevation angle tilts the view up. RX=0 down, RX=180 straight up.
    """
    return (90.0 + elevation_deg(cam_pos, target_pos), 0.0, 0.0)


def ground_range_m(cam_pos, target_pos) -> float:
    """Straight-line distance from the camera to the target (metres)."""
    dx = target_pos[0] - cam_pos[0]
    dy = target_pos[1] - cam_pos[1]
    dz = target_pos[2] - cam_pos[2]
    return sqrt(dx * dx + dy * dy + dz * dz)
