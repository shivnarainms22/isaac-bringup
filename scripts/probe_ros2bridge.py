# M0b probe: confirm the ROS 2 bridge extension can be ENABLED and then imported.
# A bare __import__ of isaacsim.ros2.bridge fails because the extension's python module
# is only added to sys.path once the extension is enabled. This probe enables it via the
# (version-stable) extension manager, then imports.
from isaacsim import SimulationApp

app = SimulationApp({"headless": True})

import omni.kit.app

mgr = omni.kit.app.get_app().get_extension_manager()
enabled = mgr.set_extension_enabled_immediate("isaacsim.ros2.bridge", True)
print(f"PROBE enable isaacsim.ros2.bridge: requested (returned {enabled!r})", flush=True)

app.update()

try:
    import isaacsim.ros2.bridge  # noqa: F401
    print("PROBE import isaacsim.ros2.bridge: OK", flush=True)
except Exception as e:  # noqa: BLE001
    print(f"PROBE import isaacsim.ros2.bridge: FAIL: {type(e).__name__}: {e}", flush=True)

# Also confirm the ROS2CameraHelper node type the camera graph needs is registered.
try:
    import omni.graph.core as og
    reg = og.get_node_type("isaacsim.ros2.bridge.ROS2CameraHelper")
    print(f"PROBE node ROS2CameraHelper: {'OK' if reg is not None else 'MISSING'}", flush=True)
except Exception as e:  # noqa: BLE001
    print(f"PROBE node ROS2CameraHelper: FAIL: {type(e).__name__}: {e}", flush=True)

app.close()
print("PROBE DONE", flush=True)
