"""Parameterized camera -> ROS 2 OmniGraph builder.

A generalization of DroneRangerIssac/setup_drone_cameras.py: one definition, reused for
the M1 minimal-scene camera and the M3 drone-body cameras (DRY). Each camera gets its own
graph (its own OnPlaybackTick) so there are no node-name collisions when building several.

Imports omni.* at module top, so this module is only importable INSIDE Isaac Sim
(not in host-side unit tests).
"""
import omni.kit.commands
import omni.graph.core as og


def create_camera_prim(camera_prim_path):
    """Create a Camera prim at the given path (idempotent-ish; errors if it already exists)."""
    omni.kit.commands.execute("CreatePrim", prim_path=camera_prim_path, prim_type="Camera")


def set_prim_transform(camera_prim_path, translate, orient_euler_deg):
    """Set a prim's local transform: translate (xyz) + rotateXYZ (Euler degrees)."""
    from pxr import UsdGeom, Gf
    import omni.usd

    stage = omni.usd.get_context().get_stage()
    prim = stage.GetPrimAtPath(camera_prim_path)
    xform = UsdGeom.Xformable(prim)
    xform.ClearXformOpOrder()
    xform.AddTranslateOp().Set(Gf.Vec3d(float(translate[0]), float(translate[1]), float(translate[2])))
    xform.AddRotateXYZOp().Set(Gf.Vec3f(float(orient_euler_deg[0]),
                                        float(orient_euler_deg[1]),
                                        float(orient_euler_deg[2])))


def build_camera_ros_graph(graph_path, camera_prim_path, topic, kind,
                           width=640, height=480, frame_id="drone_camera"):
    """Wire OnPlaybackTick -> IsaacCreateRenderProduct -> ROS2CameraHelper for one camera.

    kind: "rgb" or "depth" (passed straight to ROS2CameraHelper.inputs:type).
    """
    keys = og.Controller.Keys
    rp = "RenderProd"
    helper = "Helper"
    og.Controller.edit(
        {"graph_path": graph_path, "evaluator_name": "execution"},
        {
            keys.CREATE_NODES: [
                ("OnTick", "omni.graph.action.OnPlaybackTick"),
                (rp, "isaacsim.core.nodes.IsaacCreateRenderProduct"),
                (helper, "isaacsim.ros2.bridge.ROS2CameraHelper"),
            ],
            keys.SET_VALUES: [
                (f"{rp}.inputs:cameraPrim", [camera_prim_path]),
                (f"{rp}.inputs:width", width),
                (f"{rp}.inputs:height", height),
                (f"{helper}.inputs:topicName", topic),
                (f"{helper}.inputs:type", kind),
                (f"{helper}.inputs:frameId", frame_id),
            ],
            keys.CONNECT: [
                ("OnTick.outputs:tick", f"{rp}.inputs:execIn"),
                (f"{rp}.outputs:execOut", f"{helper}.inputs:execIn"),
                (f"{rp}.outputs:renderProductPath", f"{helper}.inputs:renderProductPath"),
            ],
        },
    )


def build_rgbd(body_path, width=640, height=480, frame_id="drone_camera"):
    """Create RGB + Depth cameras under body_path and wire both to ROS 2.

    Publishes /drone/rgb (rgb8) and /drone/depth (32FC1). Used for the M3 drone body.
    Returns the two camera prim paths so the caller can set their transforms.
    """
    rgb_cam = f"{body_path}/RGBCamera"
    depth_cam = f"{body_path}/DepthCamera"
    create_camera_prim(rgb_cam)
    create_camera_prim(depth_cam)
    build_camera_ros_graph(f"{body_path}/RGBGraph", rgb_cam, "/drone/rgb", "rgb",
                           width=width, height=height, frame_id=frame_id)
    build_camera_ros_graph(f"{body_path}/DepthGraph", depth_cam, "/drone/depth", "depth",
                           width=width, height=height, frame_id=frame_id)
    return rgb_cam, depth_cam
