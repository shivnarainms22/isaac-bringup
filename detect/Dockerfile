# Detection environment for the static-cam YOLO experiment.
# ros:jazzy matches the Isaac bridge's DDS distro (cross-distro hashes won't match Humble),
# plus Ultralytics YOLO. Built by scripts/setup_detect.sh, run by scripts/run_detect.sh.
FROM ros:jazzy

RUN apt-get update \
    && apt-get install -y --no-install-recommends python3-pip libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Ubuntu 24.04's python is externally-managed; --break-system-packages is expected here.
# ros:jazzy ships an apt-managed numpy (no pip RECORD file) that pip refuses to uninstall,
# so a bare `pip install ultralytics` aborts with "Cannot uninstall numpy ... RECORD file
# not found". Seed a pip-managed numpy into /usr/local first (--ignore-installed skips the
# un-removable distro one; it stays shadowed on sys.path), pinned <2 to keep ABI compatibility
# with the ROS 2 Jazzy python stack, then install ultralytics.
# The default linux torch wheel is CUDA-enabled, so `docker run --gpus all` uses the RTX GPU.
RUN pip3 install --no-cache-dir --break-system-packages --ignore-installed "numpy<2" \
    && pip3 install --no-cache-dir --break-system-packages "numpy<2" ultralytics

# rclpy + sensor_msgs come from the ros:jazzy base (sourced at runtime).
