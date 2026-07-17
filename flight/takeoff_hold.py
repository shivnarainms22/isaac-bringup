"""Arm the PX4 SITL drone and hold a hover at a target altitude, for the from-below test.

run_session.sh gets PX4 to "Ready for takeoff" but nothing commands a takeoff, so the drone
sits on the ground. The static-camera experiment needs it AIRBORNE to test the real checkpoint
geometry (a ground camera looking UP at a flying drone). This connects to PX4 over MAVLink,
arms, takes off to --alt, and then holds (loiter) so the drone stays put while we aim a camera
and run the detector. Prints altitude telemetry so the climb is visible.

Runs on the HOST (--network=host lets it reach PX4's MAVLink UDP directly). Needs MAVSDK:
  python3 -m venv ~/flightenv && ~/flightenv/bin/pip install mavsdk
  ~/flightenv/bin/python ~/isaac-bringup/flight/takeoff_hold.py --alt 4

MAVSDK drives PX4's arming checks + mode switches for us (more robust than raw pymavlink).
"""
import argparse
import asyncio
import sys

from mavsdk import System


def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--alt", type=float, default=4.0, help="Takeoff/hover altitude, metres.")
    p.add_argument("--url", default="udp://:14540",
                   help="MAVLink connection to PX4 (MAVSDK listens on this; PX4 SITL onboard "
                        "link defaults to udp 14540).")
    p.add_argument("--connect-timeout", type=float, default=30.0,
                   help="Seconds to wait for a PX4 connection before giving up.")
    return p.parse_args(argv)


async def wait_connected(drone, timeout):
    async def _wait():
        async for state in drone.core.connection_state():
            if state.is_connected:
                return True
    try:
        await asyncio.wait_for(_wait(), timeout=timeout)
        print("[takeoff] connected to PX4", flush=True)
    except asyncio.TimeoutError:
        print(f"[takeoff] ERROR: no PX4 connection on {timeout}s -- is the sim running and is "
              f"the MAVLink URL right?", file=sys.stderr, flush=True)
        raise


async def wait_ready(drone):
    """Wait until PX4's health flags say it's OK to arm (global position + home set)."""
    async for health in drone.telemetry.health():
        if health.is_global_position_ok and health.is_home_position_ok:
            print("[takeoff] PX4 reports position OK, ready to arm", flush=True)
            return
        print("[takeoff] waiting for position/home lock...", flush=True)
        await asyncio.sleep(1)


async def report_altitude(drone):
    """Continuously print relative altitude so the climb + hold are visible."""
    async for pos in drone.telemetry.position():
        print(f"[takeoff] altitude {pos.relative_altitude_m:5.2f} m  "
              f"(lat {pos.latitude_deg:.6f}, lon {pos.longitude_deg:.6f})", flush=True)
        await asyncio.sleep(2)


async def run(args):
    drone = System()
    await drone.connect(system_address=args.url)
    await wait_connected(drone, args.connect_timeout)
    await wait_ready(drone)

    await drone.action.set_takeoff_altitude(args.alt)
    print(f"[takeoff] arming...", flush=True)
    await drone.action.arm()
    print(f"[takeoff] taking off to {args.alt} m and holding (Ctrl-C to end)...", flush=True)
    await drone.action.takeoff()

    # Hold indefinitely, printing altitude. PX4 loiters at the takeoff altitude; keeping this
    # process alive keeps the link up so the drone stays put for the camera/detector run.
    await report_altitude(drone)


def main():
    args = parse_args()
    try:
        asyncio.run(run(args))
    except KeyboardInterrupt:
        print("\n[takeoff] interrupted; leaving PX4 in its current mode.", flush=True)
    except Exception as e:
        print(f"[takeoff] ERROR: {type(e).__name__}: {e}", file=sys.stderr, flush=True)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
