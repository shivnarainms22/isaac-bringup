"""Body-relative camera mount -> USD transform. Pure; no Isaac dependency.

The DroneRangerIssac README notes camera transforms set in the GUI are session-only
and lost on reset. We bake the mount into the bring-up script via this helper so the
field of view is reproducible every run.

Body frame convention (must match how the camera prim is parented under the drone body):
    +X = forward, +Y = right, +Z = up.  Orient is Euler XYZ in degrees.
"""
from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True)
class CameraMount:
    forward_m: float
    right_m: float
    up_m: float
    pitch_deg: float
    yaw_deg: float
    roll_deg: float


@dataclass(frozen=True)
class UsdTransform:
    translate: tuple
    orient_euler_deg: tuple


def to_usd_transform(mount: CameraMount) -> UsdTransform:
    """Convert a body-relative mount into USD translate (xyz) + orient (Euler XYZ deg)."""
    vals = [mount.forward_m, mount.right_m, mount.up_m,
            mount.pitch_deg, mount.yaw_deg, mount.roll_deg]
    if not all(isfinite(v) for v in vals):
        raise ValueError("camera mount values must be finite")
    translate = (mount.forward_m, mount.right_m, mount.up_m)
    orient_euler_deg = (mount.pitch_deg, mount.yaw_deg, mount.roll_deg)
    return UsdTransform(translate=translate, orient_euler_deg=orient_euler_deg)


# Default forward-facing mount: slightly ahead of and above body center, clear of the
# drone body (avoids the README's "camera obscured by body -> all zeros" failure).
DEFAULT_FORWARD_MOUNT = CameraMount(
    forward_m=0.15, right_m=0.0, up_m=0.03,
    pitch_deg=0.0, yaw_deg=0.0, roll_deg=0.0,
)
