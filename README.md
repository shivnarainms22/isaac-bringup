# isaac-bringup

Headless, reproducible bring-up of **Isaac Sim 5.1.0 + Pegasus + PX4 SITL** on the RTX 4080
box (`dronerangerlab`), so the drone's RGB/Depth cameras publish `/drone/rgb` + `/drone/depth`
into the **ROS 2 Jazzy** network.

**Status: M0–M3 complete & verified end-to-end (2026-07).** Headless Isaac renders; Pegasus
spawns a PX4-backed Iris; PX4 reports `Ready for takeoff!` in lockstep; RGB (640×480 rgb8) +
Depth (640×480 32FC1) stream into ROS 2 with confirmed real (non-zero) data.

## Version pins
| Component | Version |
|-----------|---------|
| Isaac Sim | 5.1.0 (container `nvcr.io/nvidia/isaac-sim:5.1.0`) |
| Pegasus Simulator | v5.1.0 |
| PX4-Autopilot | v1.14.3 |
| ROS 2 | Jazzy (`rmw_fastrtps_cpp`) |
| Micro-XRCE-DDS-Agent | v2.4.2 (built by setup, **not used in the camera path** — see below) |

## Architecture (how it actually runs)
- **PX4 runs on the HOST, not in the container.** The host-built `px4` binary is dynamically
  linked to `libgz-transport12.so.12`, which is absent in the Isaac container, so in-container
  autolaunch fails at exec. Instead PX4 runs on the host and the containerized sim connects to
  it over `--network=host`. `bringup.py --external-px4` sets `px4_autolaunch=False` for this.
- **PX4 is launched as `gazebo-classic_iris` (binary directly, NOT `make`).** In this mode PX4
  is the gazebo-classic lockstep *client* and connects out to Pegasus's `tcpin` server on TCP
  4560, and the lockstep handshake engages. Launching as `none_iris` deadlocks (wrong TCP
  direction + no handshake → PX4 `poll timeout` forever + Pegasus `Waiting for first heartbeat`).
  `make`'s gazebo target can't be used — it would start real Gazebo and hit the same missing lib.
- **Cameras reach ROS via the Isaac ROS 2 bridge (OmniGraph), over UDP-only DDS.** Isaac's
  bundled FastDDS and an external FastDDS have incompatible shared-memory segments, so SHM
  silently drops all data. Both the sim and every ROS consumer force a UDP-only profile
  (`config/fastdds_udp_only.xml`) — baked into `scripts/_entry.sh` and `verify/verify_camera.sh`.
- **Pegasus↔PX4 is MAVLink; the XRCE agent is not in this loop** (it's for the real-drone
  PX4↔ROS bridge, built by `setup.sh` for completeness).

## Daily flow (after one-time setup)
Run on the **host** (starts host PX4 + container sim with cameras):
```bash
bash scripts/run_session.sh start     # host PX4 (gazebo-classic_iris) + docker start + sim --external-px4 --cameras
bash scripts/run_session.sh status    # health check both sides + the topic-verify command
bash scripts/run_session.sh stop       # kill the sim and host PX4
```

## One-time setup (run once on the box)
```bash
bash scripts/setup.sh                  # clone+build PX4/XRCE/Pegasus into ~/droneranger-isaac (host)
bash scripts/setup_container.sh        # create the persistent root container + install Pegasus
```
First-ever PX4 run may hit a **root-owned `/tmp/px4_lock-0`** (and the box user has no sudo) —
clear it once via docker-as-root:
`docker run --rm -v /tmp:/hosttmp ros:jazzy bash -lc "rm -rf /hosttmp/px4_lock-* /hosttmp/px4-*"`.

## Verify cameras (from a Jazzy consumer, UDP-only)
```bash
# list topics (needs the UDP-only profile even for discovery over some setups):
docker run --rm --network=host --ipc=host -e ROS_DOMAIN_ID=0 -e RMW_IMPLEMENTATION=rmw_fastrtps_cpp \
  -e FASTRTPS_DEFAULT_PROFILES_FILE=/work/config/fastdds_udp_only.xml \
  -e FASTDDS_DEFAULT_PROFILES_FILE=/work/config/fastdds_udp_only.xml \
  -v ~/isaac-bringup:/work ros:jazzy bash -lc "ros2 topic list | grep -i drone"

# rate + real-pixel check per topic:
docker run --rm -it --network=host --ipc=host -e ROS_DOMAIN_ID=0 -e RMW_IMPLEMENTATION=rmw_fastrtps_cpp \
  -v ~/isaac-bringup:/work ros:jazzy bash -lc "bash /work/verify/verify_camera.sh /drone/rgb"
```
`verify/verify_camera.sh` uses a **best-effort** count subscriber (there is no `ros2 topic hz
--qos-reliability` flag) and `verify/grab_frame.py` decodes a frame to report min/max/mean and
nonzero pixel count (proves frames aren't all-black).

## Layout
- `scripts/setup.sh` — one-time host installer/builder (idempotent): PX4 v1.14.3, XRCE, Pegasus.
- `scripts/setup_container.sh` — create the persistent root container + install Pegasus editable.
- `scripts/run_session.sh` — per-session launcher (`start`/`stop`/`status`); the working recipe.
- `scripts/_entry.sh` — in-container launcher for `bringup.py`: sets ROS 2 bridge libs + UDP-only DDS.
- `scripts/probe_*.py` — M0 probes (headless import / camera-graph sanity).
- `isaac/bringup.py` — standalone headless app: load scene → spawn drone → cameras → step loop.
  Flags: `--no-vehicle` (M1), `--external-px4`, `--cameras` (M3), `--env <builtin>`, `--scene`, `--frames`.
- `isaac/camera_graph.py` — parameterized camera→ROS OmniGraph builder (`build_rgbd` = RGB+Depth).
- `isaac/camera_config.py` — body-relative camera mount → USD transform (pure, tested).
- `config/fastdds_udp_only.xml` — UDP-only FastDDS profile (SHM disabled).
- `verify/verify_camera.sh` — Jazzy consumer: topic list + rate + frame grab.
- `verify/count_topic.py` — best-effort rate counter. `verify/grab_frame.py` — pixel-stat dump.

Box workspace: `~/droneranger-isaac/` (host build) + `~/isaac-bringup` (this repo, mounted at
`/work`). Host is Ubuntu 22.04/Humble; the container is 24.04/Jazzy — always verify camera
topics from a **Jazzy** consumer.

Design: `../docs/superpowers/specs/2026-06-24-pegasus-camera-ros-bringup-design.md`
Plan: `../docs/superpowers/plans/2026-06-24-pegasus-camera-ros-bringup.md`
