# isaac-bringup

Headless, reproducible bring-up of **Isaac Sim 5.1.0 + Pegasus + PX4 SITL** on the RTX 4080
box (`dronerangerlab`), so the drone's RGB/Depth cameras publish `/drone/rgb` + `/drone/depth`
into the **ROS 2 Jazzy** network — set up once, launched daily with two commands.

## Version pins
| Component | Version |
|-----------|---------|
| Isaac Sim | 5.1.0 (container `nvcr.io/nvidia/isaac-sim:5.1.0`) |
| Pegasus Simulator | v5.1.0 |
| PX4-Autopilot | v1.14.3 |
| Micro-XRCE-DDS-Agent | v2.4.2 |
| ROS 2 | Jazzy (`rmw_fastrtps_cpp`) |

## Daily flow (after one-time setup)
```bash
bash scripts/run_session.sh          # docker start + XRCE agent + headless bringup
```

## One-time setup (run once on the box)
```bash
bash scripts/setup.sh                 # clone+build PX4/XRCE/Pegasus into /home, build the
                                      # persistent container, warm the shader cache
```

## Layout
- `scripts/setup.sh` — one-time installer/builder (idempotent).
- `scripts/run_session.sh` — per-session launcher.
- `scripts/probe_imports.py` — M0 probe: confirms headless camera-graph modules import.
- `isaac/bringup.py` — standalone headless app (load scene → spawn drone → cameras → loop).
- `isaac/camera_graph.py` — parameterized camera→ROS OmniGraph builder.
- `isaac/camera_config.py` — body-relative camera mount → USD transform (pure, tested).
- `verify/verify_camera.sh` — Jazzy consumer: `ros2 topic hz` + frame dump.

Box workspace: `/home/shivnarains/droneranger-isaac/`. Host is Ubuntu 22.04/Humble; the
container is 24.04/Jazzy — always verify camera topics from a **Jazzy** consumer.

Design: `../docs/superpowers/specs/2026-06-24-pegasus-camera-ros-bringup-design.md`
Plan: `../docs/superpowers/plans/2026-06-24-pegasus-camera-ros-bringup.md`
