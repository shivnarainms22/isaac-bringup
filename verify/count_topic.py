"""Count sensor_msgs/Image messages on a topic using a BEST_EFFORT subscriber.

Isaac's camera helper publishes BEST_EFFORT; `ros2 topic hz` uses a RELIABLE subscriber
(and has no QoS flag), so it sees nothing. A BEST_EFFORT subscriber is compatible with
both, so this is the reliable way to measure the rate.

Usage (inside a ros:jazzy env): python3 count_topic.py /drone/rgb [seconds]
"""
import sys
import time

import rclpy
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from sensor_msgs.msg import Image


def main():
    topic = sys.argv[1] if len(sys.argv) > 1 else "/drone/rgb"
    secs = float(sys.argv[2]) if len(sys.argv) > 2 else 5.0

    rclpy.init()
    node = rclpy.create_node("count_topic")
    qos = QoSProfile(depth=10,
                     reliability=ReliabilityPolicy.BEST_EFFORT,
                     history=HistoryPolicy.KEEP_LAST)

    state = {"n": 0, "w": None, "h": None, "enc": None}

    def cb(msg):
        state["n"] += 1
        state["w"], state["h"], state["enc"] = msg.width, msg.height, msg.encoding

    node.create_subscription(Image, topic, cb, qos)

    end = time.time() + secs
    while time.time() < end:
        rclpy.spin_once(node, timeout_sec=0.1)

    n = state["n"]
    rate = n / secs if secs > 0 else 0.0
    if n:
        print(f"COUNT {topic}: {n} msgs in {secs:.0f}s -> {rate:.1f} Hz "
              f"({state['w']}x{state['h']} {state['enc']})")
    else:
        print(f"COUNT {topic}: 0 msgs in {secs:.0f}s -> NOT RECEIVING")

    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
