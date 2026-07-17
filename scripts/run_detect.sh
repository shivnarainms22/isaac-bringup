#!/usr/bin/env bash
# Run the static-cam YOLO detector against the live Isaac /static_cam/rgb stream.
# The Isaac sim must already be running with --static-cam (see run_static_cam_experiment.sh).
# Any args are passed straight through to detect_static_cam.py.
#
# Usage (on the GPU box, after setup_detect.sh):
#   bash ~/isaac-bringup/scripts/run_detect.sh --frames 200    # uses detect/weights/drone.pt
#   bash ~/isaac-bringup/scripts/run_detect.sh --weights yolov8n.pt --classes airplane,bird  # COCO smoke test
set -eo pipefail

REPO="${REPO:-$HOME/isaac-bringup}"
DOMAIN="${ROS_DOMAIN_ID:-0}"

docker run --rm -it --gpus all --network=host --ipc=host \
  -e ROS_DOMAIN_ID="${DOMAIN}" \
  -e RMW_IMPLEMENTATION=rmw_fastrtps_cpp \
  -e FASTRTPS_DEFAULT_PROFILES_FILE=/work/config/fastdds_udp_only.xml \
  -e FASTDDS_DEFAULT_PROFILES_FILE=/work/config/fastdds_udp_only.xml \
  -e PYTHONPATH=/work \
  -v "${REPO}:/work" \
  droneranger-detect \
  bash -lc "source /opt/ros/jazzy/setup.bash && python3 /work/detect/detect_static_cam.py $*"
