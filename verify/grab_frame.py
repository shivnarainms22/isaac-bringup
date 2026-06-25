"""Grab one Image off a topic and report pixel stats (proves frames aren't all-zeros).

Uses a BEST_EFFORT subscriber + the UDP-only profile (set via env by verify_camera.sh
or the caller). No cv_bridge/PIL dependency: decodes the raw rgb8/depth buffer with numpy
and prints shape + min/max/mean so we can confirm real, varied pixels.

Usage (inside ros:jazzy): python3 grab_frame.py /drone/rgb [timeout_s]
"""
import sys
import time

import numpy as np
import rclpy
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from sensor_msgs.msg import Image


def main():
    topic = sys.argv[1] if len(sys.argv) > 1 else "/drone/rgb"
    timeout_s = float(sys.argv[2]) if len(sys.argv) > 2 else 10.0

    rclpy.init()
    node = rclpy.create_node("grab_frame")
    qos = QoSProfile(depth=5,
                     reliability=ReliabilityPolicy.BEST_EFFORT,
                     history=HistoryPolicy.KEEP_LAST)
    got = {"msg": None}

    def cb(msg):
        if got["msg"] is None:
            got["msg"] = msg

    node.create_subscription(Image, topic, cb, qos)

    end = time.time() + timeout_s
    while got["msg"] is None and time.time() < end:
        rclpy.spin_once(node, timeout_sec=0.1)

    msg = got["msg"]
    if msg is None:
        print(f"GRAB {topic}: no frame within {timeout_s:.0f}s")
        node.destroy_node(); rclpy.shutdown(); sys.exit(1)

    buf = np.frombuffer(bytes(msg.data), dtype=np.uint8)
    print(f"GRAB {topic}: {msg.width}x{msg.height} {msg.encoding} "
          f"step={msg.step} bytes={len(msg.data)}")
    print(f"GRAB pixels: min={int(buf.min())} max={int(buf.max())} "
          f"mean={buf.mean():.1f} nonzero={int(np.count_nonzero(buf))}/{buf.size}")
    if buf.max() == 0:
        print("GRAB WARNING: frame is ALL ZEROS (camera may be obscured or unlit)")
    else:
        print("GRAB OK: frame has real, varied pixel data")

    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
