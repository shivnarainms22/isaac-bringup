#!/usr/bin/env bash
# In-container launcher for bringup.py. Sets the env the ROS 2 bridge needs BEFORE python
# starts, then execs the bring-up. The bridge ships its own Jazzy libs but only finds them
# if jazzy/lib is on LD_LIBRARY_PATH at process start (otherwise: "Could not load
# librmw_implementation.so ... libament_index_cpp.so: cannot open shared object file").
#
# Usage (inside the Isaac container): bash /work/scripts/_entry.sh [bringup.py args...]
set -eo pipefail

BRIDGE_LIB=/isaac-sim/exts/isaacsim.ros2.bridge/jazzy/lib
export ROS_DISTRO="${ROS_DISTRO:-jazzy}"
export RMW_IMPLEMENTATION="${RMW_IMPLEMENTATION:-rmw_fastrtps_cpp}"
export LD_LIBRARY_PATH="${LD_LIBRARY_PATH:-}:${BRIDGE_LIB}"
export PYTHONUNBUFFERED=1
export PYTHONPATH="${PYTHONPATH:-/work}"
# Force UDP-only DDS transport: Isaac's bundled FastDDS and external FastDDS have
# incompatible shared-memory segments, so SHM silently drops all data. See config XML.
export FASTRTPS_DEFAULT_PROFILES_FILE="${FASTRTPS_DEFAULT_PROFILES_FILE:-/work/config/fastdds_udp_only.xml}"
export FASTDDS_DEFAULT_PROFILES_FILE="${FASTDDS_DEFAULT_PROFILES_FILE:-/work/config/fastdds_udp_only.xml}"

cd /isaac-sim
exec ./python.sh /work/isaac/bringup.py "$@"
