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
  echo "== ros2 topic hz $t (best_effort, 7s window) =="
  # best_effort subscriber is compatible with BOTH best_effort and reliable publishers;
  # Isaac's camera helper publishes best_effort, so a default (reliable) hz sees 0 msgs.
  timeout 9 ros2 topic hz "$t" --qos-reliability best_effort || echo "(no messages on $t within window)"
done
