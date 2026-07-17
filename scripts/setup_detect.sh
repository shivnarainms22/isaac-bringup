#!/usr/bin/env bash
# One-time setup for the static-cam YOLO experiment:
#   1. build the detection container image (ros:jazzy + Ultralytics YOLO)
#   2. download the public drone-detection weights -> detect/weights/drone.pt
# Needs internet. Re-run to rebuild / re-fetch (both steps are idempotent).
#
# Usage (on the GPU box): bash ~/isaac-bringup/scripts/setup_detect.sh
set -eo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"

# Public drone-detection model (YOLOv8x, ~137 MB). Detects the drone as an object -- the
# right kind for a ground camera looking UP at it. (VisDrone-style models are the WRONG kind:
# they detect objects seen FROM a drone, not the drone itself.)
WEIGHTS_URL="https://huggingface.co/doguilmak/Drone-Detection-YOLOv8x/resolve/main/weight/best.pt"
WEIGHTS_DIR="${REPO}/detect/weights"
WEIGHTS_PATH="${WEIGHTS_DIR}/drone.pt"

echo "== [1/2] building droneranger-detect from ${REPO}/detect/Dockerfile =="
docker build -t droneranger-detect -f "${REPO}/detect/Dockerfile" "${REPO}/detect"

echo "== [2/2] fetching drone-detection weights -> ${WEIGHTS_PATH} =="
mkdir -p "${WEIGHTS_DIR}"
if [ -s "${WEIGHTS_PATH}" ]; then
  echo "   already present ($(du -h "${WEIGHTS_PATH}" | cut -f1)); skipping download."
else
  curl -fL --retry 3 -o "${WEIGHTS_PATH}" "${WEIGHTS_URL}"
  echo "   downloaded $(du -h "${WEIGHTS_PATH}" | cut -f1)"
fi

echo "== done: image 'droneranger-detect' ready; weights at ${WEIGHTS_PATH} =="
