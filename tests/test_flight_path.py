"""Host-side tests for the scripted flight path (no Isaac needed)."""
import pytest

from isaac.flight_path import drone_position

# takeoff=10 frames, cruise=20 frames, span=40 m, standoff=40 m, alt=30 m
P = dict(takeoff_frames=10, cruise_frames=20, span_m=40.0, standoff_m=40.0, alt_m=30.0)


def test_starts_on_the_ground():
    x, y, z = drone_position(0, **P)
    assert z == pytest.approx(0.0)
    assert (x, y) == (-40.0, 40.0)


def test_climbs_during_takeoff():
    z_mid = drone_position(5, **P)[2]
    assert z_mid == pytest.approx(15.0)   # halfway up


def test_reaches_cruise_altitude_and_holds():
    assert drone_position(10, **P)[2] == pytest.approx(30.0)
    assert drone_position(25, **P)[2] == pytest.approx(30.0)
    assert drone_position(200, **P)[2] == pytest.approx(30.0)


def test_first_pass_sweeps_west_to_east():
    x_start = drone_position(10, **P)[0]        # start of pass 0
    x_mid = drone_position(20, **P)[0]          # middle of pass 0
    assert x_start == pytest.approx(-40.0)
    assert x_mid == pytest.approx(0.0)          # crosses the camera view at x=0


def test_second_pass_reverses_direction():
    # pass 1 begins at frame takeoff+cruise = 30, starting at +span.
    assert drone_position(30, **P)[0] == pytest.approx(40.0)
    assert drone_position(40, **P)[0] == pytest.approx(0.0)


def test_standoff_is_constant():
    for f in (0, 5, 15, 35, 100):
        assert drone_position(f, **P)[1] == pytest.approx(40.0)


def test_rejects_bad_params():
    with pytest.raises(ValueError):
        drone_position(0, takeoff_frames=0, cruise_frames=20, span_m=40, standoff_m=40, alt_m=30)
