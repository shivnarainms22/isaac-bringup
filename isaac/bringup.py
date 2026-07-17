"""Headless Isaac Sim bring-up: spawn a Pegasus/PX4 drone and publish camera frames to ROS 2.

Modes:
  --no-vehicle : M1 minimal scene (ground + lit cube + overhead camera -> /drone/rgb).
                 Proves the bridge + host-net DDS + headless render with no Pegasus/PX4.
  (default)    : M2 - load --scene (Env.usd), Pegasus spawns the PX4-backed drone
                 (PX4 autolaunched from --px4-dir, MAVLink HIL). Add --cameras for M3:
                 attach RGB+Depth cameras to the drone body and publish /drone/rgb+/drone/depth.

Run inside the Isaac container with the repo root on PYTHONPATH (scripts/_entry.sh does this):
  PYTHONPATH=/work ./python.sh /work/isaac/bringup.py --frames 0            # M2 spawn
  PYTHONPATH=/work ./python.sh /work/isaac/bringup.py --cameras --frames 0  # M3 + cameras
  PYTHONPATH=/work ./python.sh /work/isaac/bringup.py --no-vehicle          # M1

Prints lines prefixed "BRINGUP " (always flush=True) so progress survives a piped stdout.
"""
import argparse

from isaacsim import SimulationApp


def log(msg):
    print(f"BRINGUP {msg}", flush=True)


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--no-vehicle", action="store_true",
                   help="M1: minimal scene + one camera, no Pegasus/PX4.")
    p.add_argument("--scene", default="/ws/DroneRangerIssac/Env.usd",
                   help="USD scene to load via Pegasus (default: the project Env.usd).")
    p.add_argument("--px4-dir", default="/ws/PX4-Autopilot",
                   help="PX4-Autopilot dir Pegasus autolaunches PX4 from.")
    p.add_argument("--external-px4", action="store_true",
                   help="Do NOT autolaunch PX4 in-container; connect to a PX4 already "
                        "running on the host (over --network=host). Use when the container's "
                        "PX4 binary can't load its host-built libs (e.g. libgz-transport).")
    p.add_argument("--env", default=None,
                   help="Use a Pegasus built-in environment by name (e.g. 'Curved Gridroom') "
                        "instead of --scene. Isolates PX4/heartbeat from Env.usd loading.")
    p.add_argument("--cameras", action="store_true",
                   help="M3: attach RGB+Depth cameras to the drone body, publish to ROS 2.")
    p.add_argument("--static-cam", action="store_true",
                   help="Static-cam experiment: add a fixed ground camera looking up at the "
                        "drone, publishing /static_cam/rgb (for the ground-viewpoint YOLO test).")
    p.add_argument("--static-cam-pos", type=float, nargs=3, default=None,
                   metavar=("X", "Y", "Z"),
                   help="World position of the static ground camera (default from static_cam.py).")
    p.add_argument("--static-cam-euler", type=float, nargs=3, default=None,
                   metavar=("RX", "RY", "RZ"),
                   help="USD RotateXYZ Euler degrees for the static camera aim "
                        "(default from static_cam.py; tune with verify/grab_frame.py).")
    p.add_argument("--scene-light", type=float, default=0.0,
                   help="Add a dome light of this intensity to brighten a dark scene for the "
                        "detection test (0 = off; try ~2000-3000 for Curved Gridroom).")
    p.add_argument("--drone-prop-alt", type=float, default=0.0,
                   help="From-below detection test: hold a static drone at this altitude (m), "
                        "no PX4/physics, ground camera auto-aimed up at it. 0 = off.")
    p.add_argument("--drone-prop-standoff", type=float, default=5.0,
                   help="Horizontal distance (m) of the ground camera from the drone prop "
                        "(used with --drone-prop-alt). Increase to test detection at range.")
    p.add_argument("--frames", type=int, default=600,
                   help="Number of render steps to run, then exit. 0 = run until killed.")
    p.add_argument("--width", type=int, default=640, help="Camera width (px).")
    p.add_argument("--height", type=int, default=480, help="Camera height (px).")
    return p.parse_args()


def enable_ros2_bridge(app):
    """Enable the ROS 2 bridge extension so ROS2CameraHelper is available (see M0b probe)."""
    import omni.kit.app
    mgr = omni.kit.app.get_app().get_extension_manager()
    ok = mgr.set_extension_enabled_immediate("isaacsim.ros2.bridge", True)
    app.update()
    log(f"ros2 bridge enabled: {ok}")


def build_minimal_scene(world, width=640, height=480):
    """M1: ground plane + a lit red cube + an overhead camera. Returns the camera prim path."""
    import numpy as np
    from pxr import UsdLux, Sdf
    import omni.usd
    from isaacsim.core.api.objects import VisualCuboid
    from isaac.camera_graph import create_camera_prim, set_prim_transform, build_camera_ros_graph

    world.scene.add_default_ground_plane()
    log("ground plane added")
    VisualCuboid(prim_path="/World/Cube", name="cube",
                 position=np.array([0.0, 0.0, 0.5]), scale=np.array([1.0, 1.0, 1.0]),
                 color=np.array([1.0, 0.1, 0.1]))
    log("cube added")

    stage = omni.usd.get_context().get_stage()
    dome = UsdLux.DomeLight.Define(stage, Sdf.Path("/World/DomeLight"))
    dome.CreateIntensityAttr(1000.0)
    log("dome light added")

    cam_path = "/World/OverheadCam"
    create_camera_prim(cam_path)
    set_prim_transform(cam_path, translate=(0.0, 0.0, 5.0), orient_euler_deg=(0.0, 0.0, 0.0))
    build_camera_ros_graph("/World/CamGraph", cam_path, "/drone/rgb", "rgb",
                           width=width, height=height)
    log(f"minimal scene built: /drone/rgb publisher ({width}x{height}) on overhead camera")
    return cam_path


def build_drone_from_below_scene(alt, standoff, light, width=640, height=480):
    """Detection test: a drone model held STATIC at altitude, ground camera auto-aimed up at it.

    No PX4, no Pegasus, no physics -- we place the Iris mesh at (0,0,alt) and point a ground
    camera up at it from (0,-standoff,0.3), publishing /static_cam/rgb. This validates the
    from-below viewpoint (drone at flight height, against a dark 'sky' background, at a chosen
    range) without depending on working flight dynamics. Sweep `standoff`/`alt` to test range.
    """
    from pxr import UsdLux, Sdf
    import omni.usd
    from pegasus.simulator.params import ROBOTS
    from isaac.camera_graph import create_camera_prim, set_prim_transform, build_camera_ros_graph
    from isaac.static_cam import look_up_euler_deg, ground_range_m

    stage = omni.usd.get_context().get_stage()

    # A dome light FAILS for a from-below shot: looking up, the dome IS the background, so it
    # lights the drone and the "sky" to the same grey -> near-zero contrast (the drone vanishes).
    # Instead light the drone from below with a distant light shining UP (euler 180 flips its
    # default downward emission to upward), leaving the background dark. That reproduces the
    # lit-drone-on-dark-background look that gave the 0.76 grounded detection.
    sun = UsdLux.DistantLight.Define(stage, Sdf.Path("/World/SunLight"))
    sun.CreateIntensityAttr(float(light))
    set_prim_transform("/World/SunLight", translate=(0.0, 0.0, 0.0), orient_euler_deg=(180.0, 0.0, 0.0))
    log(f"distant light (shining up) added: intensity {light}")

    # Reference the Iris mesh as a plain, static prop at altitude (we never step physics, so
    # it simply hangs there).
    drone_path = "/World/DroneProp"
    prim = stage.DefinePrim(drone_path, "Xform")
    prim.GetReferences().AddReference(ROBOTS["Iris"])
    set_prim_transform(drone_path, translate=(0.0, 0.0, float(alt)), orient_euler_deg=(0.0, 0.0, 0.0))
    log(f"drone prop placed at altitude {alt} m (static, no physics)")

    cam_pos = (0.0, -float(standoff), 0.3)
    target = (0.0, 0.0, float(alt))
    euler = look_up_euler_deg(cam_pos, target)
    cam_path = "/World/StaticGroundCam"
    create_camera_prim(cam_path)
    set_prim_transform(cam_path, cam_pos, euler)
    build_camera_ros_graph("/World/StaticCamGraph", cam_path, "/static_cam/rgb", "rgb",
                           width=width, height=height, frame_id="static_cam")
    log(f"static ground camera at {cam_pos} auto-aimed up at {target} (euler {euler}), "
        f"range ~{ground_range_m(cam_pos, target):.1f} m -> /static_cam/rgb")


def render_only_loop(app, frames):
    """Play the timeline and update the app (renders + ticks camera graphs) WITHOUT stepping
    physics -- so a static prop stays put. Used by the from-below detection scene."""
    import omni.timeline
    timeline = omni.timeline.get_timeline_interface()
    timeline.play()
    log(f"timeline playing (render-only); {'until killed' if frames == 0 else frames} frames")
    i = 0
    while frames == 0 or i < frames:
        app.update()
        i += 1
        if i % 120 == 0:
            log(f"rendered {i} frames")
    log(f"done after {i} frames")


def build_pegasus_vehicle(scene, px4_dir, env_name=None, px4_autolaunch=True):
    """M2: Pegasus interface + World, load the scene, spawn a PX4-backed Iris drone.

    Mirrors PegasusSimulator examples/1_px4_single_vehicle.py. Pegasus owns the World
    singleton (do NOT create our own). If px4_autolaunch, PX4 is launched from px4_dir;
    otherwise Pegasus connects to a PX4 already running externally (e.g. on the host over
    --network=host). If env_name is given, loads that built-in environment instead of `scene`.
    """
    from omni.isaac.core.world import World
    from scipy.spatial.transform import Rotation
    from pegasus.simulator.params import ROBOTS, SIMULATION_ENVIRONMENTS
    from pegasus.simulator.logic.backends.px4_mavlink_backend import (
        PX4MavlinkBackend, PX4MavlinkBackendConfig)
    from pegasus.simulator.logic.vehicles.multirotor import Multirotor, MultirotorConfig
    from pegasus.simulator.logic.interface.pegasus_interface import PegasusInterface

    pg = PegasusInterface()
    pg._world = World(**pg._world_settings)
    world = pg.world
    log("pegasus interface + world created")

    if env_name:
        pg.load_environment(SIMULATION_ENVIRONMENTS[env_name])
        log(f"environment loaded (builtin): {env_name}")
    else:
        pg.load_environment(scene)
        log(f"environment loaded: {scene}")

    config = MultirotorConfig()
    mavlink_config = PX4MavlinkBackendConfig({
        "vehicle_id": 0,
        "px4_autolaunch": px4_autolaunch,
        "px4_dir": px4_dir,
        "px4_vehicle_model": pg.px4_default_airframe,  # >= v1.14 uses the default airframe
    })
    config.backends = [PX4MavlinkBackend(mavlink_config)]

    Multirotor(
        "/World/quadrotor",
        ROBOTS["Iris"],
        0,
        [0.0, 0.0, 0.07],
        Rotation.from_euler("XYZ", [0.0, 0.0, 0.0], degrees=True).as_quat(),
        config=config,
    )
    if px4_autolaunch:
        log(f"multirotor spawned (Iris) with PX4 autolaunch from {px4_dir}")
    else:
        log("multirotor spawned (Iris); connecting to EXTERNAL PX4 (no autolaunch)")
    return pg, world


def attach_drone_cameras(width=640, height=480):
    """M3: RGB+Depth cameras parented to the drone body, published to ROS 2."""
    from isaac.camera_graph import build_rgbd, set_prim_transform
    from isaac.camera_config import DEFAULT_FORWARD_MOUNT, to_usd_transform

    body = "/World/quadrotor/body/body"  # matches DroneRangerIssac/setup_drone_cameras.py
    rgb_cam, depth_cam = build_rgbd(body, width=width, height=height)
    t = to_usd_transform(DEFAULT_FORWARD_MOUNT)
    set_prim_transform(rgb_cam, t.translate, t.orient_euler_deg)
    set_prim_transform(depth_cam, t.translate, t.orient_euler_deg)
    log("drone cameras attached: /drone/rgb + /drone/depth on body")


def add_scene_light(intensity):
    """Add a dome light to brighten a dark scene (e.g. Curved Gridroom) for the detection test.

    The dim builtin env leaves the drone nearly black, which starves the detector of contrast.
    A dome light lifts overall illumination so the drone reads clearly. Mirrors the M1 minimal
    scene's DomeLight. Idempotent-ish: defines a uniquely-named prim.
    """
    from pxr import UsdLux, Sdf
    import omni.usd

    stage = omni.usd.get_context().get_stage()
    dome = UsdLux.DomeLight.Define(stage, Sdf.Path("/World/ExperimentDomeLight"))
    dome.CreateIntensityAttr(float(intensity))
    log(f"scene dome light added: intensity {intensity}")


def attach_static_ground_camera(translate, orient_euler_deg, width=640, height=480):
    """Static-cam experiment: a fixed WORLD camera on the ground, aimed up at the drone.

    Publishes /static_cam/rgb. Not parented to the drone -- it stands off in the scene like
    a security camera looking up/across, the viewpoint the drone's own detector never sees.
    Reuses the same camera->ROS graph builder as the drone cameras (DRY).
    """
    from isaac.camera_graph import create_camera_prim, set_prim_transform, build_camera_ros_graph
    from isaac.static_cam import elevation_deg, ground_range_m, NOMINAL_DRONE_HOVER

    cam_path = "/World/StaticGroundCam"
    create_camera_prim(cam_path)
    set_prim_transform(cam_path, translate, orient_euler_deg)
    build_camera_ros_graph("/World/StaticCamGraph", cam_path, "/static_cam/rgb", "rgb",
                           width=width, height=height, frame_id="static_cam")
    elev = elevation_deg(translate, NOMINAL_DRONE_HOVER)
    rng = ground_range_m(translate, NOMINAL_DRONE_HOVER)
    log(f"static ground camera attached: /static_cam/rgb at {tuple(translate)} "
        f"euler {tuple(orient_euler_deg)}")
    log(f"  suggested aim: elevation ~{elev:.1f} deg, range ~{rng:.1f} m to nominal hover "
        f"{NOMINAL_DRONE_HOVER} -- tune euler with verify/grab_frame.py if the drone is off-frame")


def run_loop(world, frames):
    """Play the timeline (so OnPlaybackTick fires) and step the sim, rendering each frame."""
    import omni.timeline
    timeline = omni.timeline.get_timeline_interface()
    timeline.play()
    log(f"timeline playing; stepping {'until killed' if frames == 0 else frames} frames")
    i = 0
    while frames == 0 or i < frames:
        world.step(render=True)
        i += 1
        if i % 120 == 0:
            log(f"stepped {i} frames")
    log(f"done after {i} frames")


def main():
    import traceback
    args = parse_args()
    app = SimulationApp({"headless": True})
    try:
        if args.no_vehicle or args.cameras or args.static_cam or args.drone_prop_alt > 0.0:
            enable_ros2_bridge(app)

        if args.drone_prop_alt > 0.0:
            light = args.scene_light if args.scene_light > 0.0 else 3000.0
            build_drone_from_below_scene(args.drone_prop_alt, args.drone_prop_standoff, light,
                                         width=args.width, height=args.height)
            log("from-below scene built")
            render_only_loop(app, args.frames)
        elif args.no_vehicle:
            from isaacsim.core.api import World
            world = World()
            log("world created")
            build_minimal_scene(world, width=args.width, height=args.height)
            world.reset()
            log("world reset")
            run_loop(world, args.frames)
        else:
            pg, world = build_pegasus_vehicle(args.scene, args.px4_dir, env_name=args.env,
                                              px4_autolaunch=not args.external_px4)
            if args.cameras:
                attach_drone_cameras(width=args.width, height=args.height)
            if args.static_cam:
                from isaac.static_cam import DEFAULT_STATIC_CAM
                pos = args.static_cam_pos if args.static_cam_pos is not None \
                    else DEFAULT_STATIC_CAM.translate
                euler = args.static_cam_euler if args.static_cam_euler is not None \
                    else DEFAULT_STATIC_CAM.orient_euler_deg
                attach_static_ground_camera(pos, euler, width=args.width, height=args.height)
            if args.scene_light > 0.0:
                add_scene_light(args.scene_light)
            world.reset()
            log("world reset")
            run_loop(world, args.frames)
    except BaseException as e:  # surface the real error before Isaac's hard shutdown
        log(f"ERROR: {type(e).__name__}: {e}")
        log("TRACEBACK:\n" + traceback.format_exc())
    finally:
        app.close()
        log("app closed")


if __name__ == "__main__":
    main()
