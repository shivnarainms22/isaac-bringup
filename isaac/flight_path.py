"""Scripted drone flight path for the Isaac perception demo. Pure; no Isaac dependency.

Kinematic (not PX4-driven) so the demo is reliable regardless of the sim's flight dynamics:
the drone takes off straight up to cruise altitude, then flies level back-and-forth passes
across the static camera's view. Coordinates are world metres with the camera near the origin.

Frame convention (matches the static camera looking north-and-up):
    x = east (the drone sweeps along x), y = north (fixed standoff from the camera),
    z = up. The camera sits near (0, 0, ~0.5) and looks up at (0, standoff, alt).
"""
from math import isfinite


def drone_position(frame, takeoff_frames, cruise_frames, span_m, standoff_m, alt_m):
    """(x, y, z) world position of the drone at a given render frame.

    Phase 1 (frame < takeoff_frames): rise in place from the ground to alt_m at x = -span.
    Phase 2 (after): level passes at alt_m, sweeping x in [-span, +span], direction alternating
    each pass so it flies back and forth across the camera view (loops forever).
    """
    for v in (takeoff_frames, cruise_frames, span_m, standoff_m, alt_m):
        if not isfinite(v):
            raise ValueError("flight params must be finite")
    if takeoff_frames <= 0 or cruise_frames <= 0:
        raise ValueError("takeoff_frames and cruise_frames must be positive")

    if frame < takeoff_frames:
        z = alt_m * (frame / takeoff_frames)
        return (-span_m, standoff_m, z)

    c = frame - takeoff_frames
    pass_idx = c // cruise_frames
    frac = (c % cruise_frames) / cruise_frames
    if pass_idx % 2 == 0:                      # even pass: west -> east
        x = -span_m + 2.0 * span_m * frac
    else:                                       # odd pass: east -> west
        x = span_m - 2.0 * span_m * frac
    return (x, standoff_m, alt_m)
