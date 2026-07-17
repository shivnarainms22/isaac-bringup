#!/usr/bin/env bash
# Daily launcher for the Isaac Sim + Pegasus + PX4 camera->ROS bring-up on the GPU box.
# Encodes the working M2/M3 recipe. Run on the HOST (not inside the container):
#
#   bash scripts/run_session.sh start    # (default) host PX4 + Isaac/Pegasus sim w/ cameras
#   bash scripts/run_session.sh stop     # kill the sim and host PX4
#   bash scripts/run_session.sh status   # quick health check of both sides
#
# WHY PX4 runs on the host: the host-built px4 binary is dynamically linked to
# libgz-transport12.so.12, which is absent in the Isaac container, so px4_autolaunch fails
# there. We launch PX4 on the host as PX4_SIM_MODEL=gazebo-classic_iris (the binary DIRECTLY,
# NOT `make` -- its gazebo target would start real Gazebo and hit the same missing lib). In
# that mode PX4 is the gazebo-classic lockstep CLIENT and connects OUT to Pegasus's tcpin
# server on TCP 4560. The container sim uses --external-px4 to skip autolaunch and reach PX4
# over --network=host. (Launching PX4 as `none_iris` instead deadlocks: wrong TCP direction
# + no lockstep handshake.)
set -uo pipefail

PX4_DIR="${PX4_DIR:-$HOME/droneranger-isaac/PX4-Autopilot}"
PX4_BIN="$PX4_DIR/build/px4_sitl_default/bin/px4"
PX4_ROMFS="$PX4_DIR/ROMFS/px4fmu_common"
PX4_RCS="$PX4_ROMFS/init.d-posix/rcS"
PX4_RUN="${PX4_RUN:-$HOME/px4_run}"
PX4_LOG="${PX4_LOG:-$HOME/px4.log}"
SIM_LOG="${SIM_LOG:-$HOME/m2.log}"
CONTAINER="${CONTAINER:-isaac-droneranger}"
ENV_NAME="${ENV_NAME:-Curved Gridroom}"   # builtin env; set ENV_NAME="" to use --scene Env.usd

start_px4() {
  echo "[run_session] killing any stale PX4..."
  pkill -9 -f "px4_sitl_default/bin/px4" 2>/dev/null || true
  sleep 1
  # Remove stale lock. First-ever run may have a root-owned /tmp/px4_lock-0 (created by an
  # earlier root process) that this rm can't touch and the user has no sudo -- in that one
  # case clear it via docker-as-root:
  #   docker run --rm -v /tmp:/hosttmp ros:jazzy bash -lc "rm -rf /hosttmp/px4_lock-* /hosttmp/px4-*"
  rm -f /tmp/px4_lock-0 2>/dev/null || true
  mkdir -p "$PX4_RUN"
  if [ ! -x "$PX4_BIN" ]; then
    echo "[run_session] ERROR: PX4 binary not found/executable at $PX4_BIN" >&2
    return 1
  fi
  echo "[run_session] starting host PX4 (gazebo-classic_iris)..."
  ( cd "$PX4_RUN" && PX4_SIM_MODEL=gazebo-classic_iris \
      nohup "$PX4_BIN" "$PX4_ROMFS/" -s "$PX4_RCS" -i 0 -d < /dev/null > "$PX4_LOG" 2>&1 & )
  for _ in $(seq 1 20); do
    if grep -q "Waiting for simulator to accept connection" "$PX4_LOG" 2>/dev/null; then
      echo "[run_session] PX4 up, listening for the simulator on TCP 4560."
      return 0
    fi
    if grep -q "already running" "$PX4_LOG" 2>/dev/null; then
      echo "[run_session] ERROR: PX4 says instance 0 already running -- kill it and retry." >&2
      return 1
    fi
    sleep 1
  done
  echo "[run_session] WARNING: no 'Waiting for simulator' within 20s; check $PX4_LOG" >&2
}

start_sim() {
  echo "[run_session] starting container + Isaac/Pegasus sim (with cameras)..."
  docker start "$CONTAINER" >/dev/null
  docker exec "$CONTAINER" pkill -f bringup.py 2>/dev/null || true
  local env_arg=()
  [ -n "$ENV_NAME" ] && env_arg=(--env "$ENV_NAME")
  # Set STATIC_CAM=1 to also publish /static_cam/rgb from a ground camera looking up at the
  # drone (the static-cam YOLO experiment). See detect/README.md + scripts/run_detect.sh.
  local static_arg=()
  [ -n "${STATIC_CAM:-}" ] && static_arg=(--static-cam)
  nohup docker exec "$CONTAINER" bash /work/scripts/_entry.sh \
      "${env_arg[@]}" --external-px4 --cameras "${static_arg[@]}" --frames 0 > "$SIM_LOG" 2>&1 &
  echo "[run_session] sim launching. Watch it:  tail -f $SIM_LOG"
  echo "[run_session] (expect: ros2 bridge enabled -> multirotor spawned -> cameras attached -> stepped)"
  [ -n "${STATIC_CAM:-}" ] && echo "[run_session] static cam ON -> also publishing /static_cam/rgb"
}

stop_all() {
  echo "[run_session] stopping sim + PX4..."
  docker exec "$CONTAINER" pkill -f bringup.py 2>/dev/null || true
  pkill -9 -f "px4_sitl_default/bin/px4" 2>/dev/null || true
  echo "[run_session] stopped."
}

status() {
  echo "== PX4 ($PX4_LOG) =="
  grep -iE "Simulator connected|Ready for takeoff|poll timeout|already running" "$PX4_LOG" 2>/dev/null | tail -5 || echo "(no px4 log yet)"
  echo "== SIM ($SIM_LOG) =="
  grep -iE "cameras attached|static ground camera|Waiting for first|ERROR|Traceback|stepped" "$SIM_LOG" 2>/dev/null | tail -6 || echo "(no sim log yet)"
  echo "== verify camera topics (UDP-only ros:jazzy consumer) =="
  echo "docker run --rm --network=host --ipc=host -e ROS_DOMAIN_ID=0 -e RMW_IMPLEMENTATION=rmw_fastrtps_cpp -e FASTRTPS_DEFAULT_PROFILES_FILE=/work/config/fastdds_udp_only.xml -e FASTDDS_DEFAULT_PROFILES_FILE=/work/config/fastdds_udp_only.xml -v \$HOME/isaac-bringup:/work ros:jazzy bash -lc 'ros2 topic list | grep -i drone'"
}

case "${1:-start}" in
  start)  start_px4 && start_sim ;;
  stop)   stop_all ;;
  status) status ;;
  *) echo "usage: $0 {start|stop|status}" >&2; exit 2 ;;
esac
