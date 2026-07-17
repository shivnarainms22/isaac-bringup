# Detection environment for the static-cam YOLO experiment.
# ros:jazzy matches the Isaac bridge's DDS distro (cross-distro hashes won't match Humble),
# plus Ultralytics YOLO. Built by scripts/setup_detect.sh, run by scripts/run_detect.sh.
FROM ros:jazzy

RUN apt-get update \
    && apt-get install -y --no-install-recommends python3-pip libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Ubuntu 24.04's python is externally-managed; --break-system-packages is expected here.
# The default linux torch wheel is CUDA-enabled, so `docker run --gpus all` uses the RTX GPU.
RUN pip3 install --no-cache-dir --break-system-packages ultralytics

# rclpy + sensor_msgs come from the ros:jazzy base (sourced at runtime).
