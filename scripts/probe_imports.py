# M0 import probe.
# Run INSIDE the Isaac container via ./python.sh. Confirms the modules the camera
# action graph needs actually import under headless/standalone mode in THIS image.
# The DroneRangerIssac README warns of `omni.kit.usd ModuleNotFoundError` in 5.1.0-rc.19
# standalone mode -> this probe tells us whether the scripted path is viable here.
from isaacsim import SimulationApp

app = SimulationApp({"headless": True})

modules = [
    "omni.kit.commands",
    "omni.graph.core",
    "omni.usd",
    "isaacsim.core.api",
    "isaacsim.ros2.bridge",
    "isaacsim.core.nodes",
]

results = {}
for mod in modules:
    try:
        __import__(mod)
        results[mod] = "OK"
    except Exception as e:  # noqa: BLE001 - the probe wants to report every failure
        results[mod] = f"FAIL: {type(e).__name__}: {e}"

for mod, status in results.items():
    print(f"PROBE {mod}: {status}")

all_ok = all(v == "OK" for v in results.values())
print(f"PROBE RESULT: {'ALL_OK' if all_ok else 'SOME_FAILED'}")

app.close()
print("PROBE DONE")
