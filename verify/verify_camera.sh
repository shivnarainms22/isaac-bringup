#!/usr/bin/env bash
# Verify camera topics from a ROS 2 JAZZY environment (host is Humble -> cross-distro
# hashes won't match, so always verify from Jazzy). Run inside a ros:jazzy container on
# --network=host with the same ROS_DOMAIN_ID as the publisher.
#
# Usage: bash verify_camera.sh /drone/rgb [/drone/depth ...]
set -eo pipefail  # NOT -u: ROS setup.bash references unbound vars

export RMW_IMPLEMENTATION="${RMW_IMPLEMENTATION:-rmw_fastrtps_cpp}"
export ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-0}"
source /opt/ros/jazzy/setup.bash

echo "== ros2 topic list (grep drone/fmu) =="
ros2 topic list | grep -E "drone|fmu" || echo "(no drone/fmu topics seen)"

for t in "$@"; do
  echo "== rate $t (best_effort subscriber, 5s) =="
  # `ros2 topic hz` has no QoS flag and uses a RELIABLE subscriber -> 0 msgs from Isaac's
  # best_effort camera publisher. A best_effort subscriber is compatible with both.
  python3 /work/verify/count_topic.py "$t" 5 || echo "(failed measuring $t)"
done
