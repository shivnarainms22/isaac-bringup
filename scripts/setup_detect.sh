#!/usr/bin/env bash
# Build the detection container image (ros:jazzy + Ultralytics YOLO) once.
# Needs internet (pulls ros:jazzy + torch/ultralytics wheels). Re-run only to rebuild.
#
# Usage (on the GPU box): bash ~/isaac-bringup/scripts/setup_detect.sh
set -eo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
echo "== building droneranger-detect from ${REPO}/detect/Dockerfile =="
docker build -t droneranger-detect -f "${REPO}/detect/Dockerfile" "${REPO}/detect"
echo "== done: image 'droneranger-detect' ready =="
