"""Headless Isaac Sim bring-up: publish camera frames into the ROS 2 network.

Modes:
  --no-vehicle : M1 minimal scene (ground + lit cube + one overhead camera -> /drone/rgb).
                 Proves the bridge + host-net DDS + headless render with no Pegasus/PX4.
  (default)    : M2/M3 path (load --scene, Pegasus-spawn the drone, cameras on the body).
                 Implemented in later tasks.

Run inside the Isaac container with the repo root on PYTHONPATH, e.g.:
  PYTHONPATH=/work ./python.sh /work/isaac/bringup.py --no-vehicle --frames 1200

Prints lines prefixed "BRINGUP " so progress survives a piped stdout (always flush=True).
"""
import argparse

from isaacsim import SimulationApp


def log(msg):
    print(f"BRINGUP {msg}", flush=True)


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--no-vehicle", action="store_true",
                   help="M1: minimal scene + one camera, no Pegasus/PX4.")
    p.add_argument("--scene", default=None, help="Path to a USD scene (e.g. Env.usd).")
    p.add_argument("--frames", type=int, default=600,
                   help="Number of render steps to run, then exit. 0 = run until killed.")
    return p.parse_args()


def enable_ros2_bridge(app):
    """Enable the ROS 2 bridge extension so ROS2CameraHelper is available (see M0b probe)."""
    import omni.kit.app
    mgr = omni.kit.app.get_app().get_extension_manager()
    ok = mgr.set_extension_enabled_immediate("isaacsim.ros2.bridge", True)
    app.update()
    log(f"ros2 bridge enabled: {ok}")


def build_minimal_scene(world):
    """Ground plane + a lit red cube + an overhead camera. Returns the camera prim path."""
    from pxr import UsdLux, Sdf, Gf
    import omni.usd
    from isaacsim.core.api.objects import VisualCuboid
    from isaac.camera_graph import create_camera_prim, set_prim_transform, build_camera_ros_graph

    world.scene.add_default_ground_plane()
    VisualCuboid(prim_path="/World/Cube", name="cube",
                 position=Gf.Vec3f(0.0, 0.0, 0.5), scale=Gf.Vec3f(1.0, 1.0, 1.0),
                 color=[1.0, 0.1, 0.1])

    # Dome light so the RGB frame isn't black.
    stage = omni.usd.get_context().get_stage()
    dome = UsdLux.DomeLight.Define(stage, Sdf.Path("/World/DomeLight"))
    dome.CreateIntensityAttr(1000.0)

    cam_path = "/World/OverheadCam"
    create_camera_prim(cam_path)
    # Default USD camera looks down -Z; placed 5 m up with no rotation it looks straight
    # down at the cube/ground -> guaranteed non-blank frame.
    set_prim_transform(cam_path, translate=(0.0, 0.0, 5.0), orient_euler_deg=(0.0, 0.0, 0.0))
    build_camera_ros_graph("/World/CamGraph", cam_path, "/drone/rgb", "rgb")
    log("minimal scene built: /drone/rgb publisher on overhead camera")
    return cam_path


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
    args = parse_args()
    app = SimulationApp({"headless": True})
    try:
        enable_ros2_bridge(app)
        from isaacsim.core.api import World
        world = World()

        if args.no_vehicle:
            build_minimal_scene(world)
        else:
            raise SystemExit("BRINGUP vehicle path not implemented yet (M2/M3).")

        world.reset()
        run_loop(world, args.frames)
    finally:
        app.close()
        log("app closed")


if __name__ == "__main__":
    main()
