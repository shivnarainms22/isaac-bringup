#!/usr/bin/env bash
# ONE-TIME container setup: create the persistent root Isaac container (with /home mounts +
# caches) and install Pegasus into Isaac's python. Run AFTER setup.sh (host build) finishes.
# Idempotent: re-run safely (skips an existing container). Daily use = scripts/run_session.sh.
set -eo pipefail

WS="$HOME/droneranger-isaac"
REPO="$HOME/isaac-bringup"
CACHE="$HOME/isaac-cache"
CON=isaac-droneranger
IMG=nvcr.io/nvidia/isaac-sim:5.1.0
mkdir -p "$CACHE/kit" "$CACHE/ov" "$CACHE/logs"

echo "STAGE C1: create persistent root container"
if ! docker ps -a --format '{{.Names}}' | grep -qx "$CON"; then
  docker create --name "$CON" --user root --gpus all --network=host --ipc=host \
    -e ACCEPT_EULA=Y -e PRIVACY_CONSENT=Y \
    -e ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-0}" -e RMW_IMPLEMENTATION=rmw_fastrtps_cpp \
    -e ROS_DISTRO=jazzy -e PYTHONUNBUFFERED=1 \
    -v "$WS":/ws -v "$REPO":/work \
    -v "$CACHE/kit":/isaac-sim/kit/cache -v "$CACHE/ov":/root/.cache/ov \
    --entrypoint sleep "$IMG" infinity
  echo "  created $CON"
else
  echo "  $CON already exists"
fi
docker start "$CON" >/dev/null
echo "  started $CON"

dex() { docker exec "$CON" bash -lc "$1"; }

echo "STAGE C2: install Pegasus into Isaac python (editable)"
dex 'cd /isaac-sim && ISAACSIM_PATH=/isaac-sim ./python.sh -m pip install -e /ws/PegasusSimulator/extensions/pegasus.simulator'

echo "STAGE C3: register Pegasus extension"
dex 'mkdir -p /isaac-sim/extsUser && ln -sf /ws/PegasusSimulator/extensions/pegasus.simulator /isaac-sim/extsUser/pegasus.simulator && echo "  linked"'

echo "SETUP CONTAINER COMPLETE"
