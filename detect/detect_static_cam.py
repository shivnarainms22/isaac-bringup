"""Run YOLO on the Isaac ground-camera stream and answer: does it see the drone?

Subscribes to a ROS 2 rgb8 image topic (default /static_cam/rgb, published by the Isaac
static ground camera), runs an Ultralytics YOLO model on each frame, and after N frames
prints a verdict (DETECTED / INTERMITTENT / NOT_DETECTED) via detect.detection_summary.

This is the experiment that de-risks the whole static-camera idea: a ground camera looks
UP at the drone, a viewpoint the drone's own detector never trains on -- so we must check
whether a detector fires at all before building the ROS checkpoint pipeline around it.

Runs in a ROS 2 (Jazzy) + Ultralytics environment -- see scripts/setup_detect.sh and
scripts/run_detect.sh. Reads the raw Image buffer directly (no cv_bridge dependency):
sensor_msgs/Image IS the raw pixel matrix.

Usage (inside the detect container, repo on PYTHONPATH):
  python3 /work/detect/detect_static_cam.py --weights /work/detect/weights/drone.pt --frames 200
"""
import argparse
import sys

import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from sensor_msgs.msg import Image

from detect.detection_summary import FrameResult, format_summary, summarize


def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--weights", default="yolov8n.pt",
                   help="Ultralytics YOLO weights. Point at your project's DRONE detector "
                        "for the real signal; yolov8n.pt (COCO) only smoke-tests the pipeline "
                        "(COCO has no 'drone' class).")
    p.add_argument("--topic", default="/static_cam/rgb", help="rgb8 image topic to subscribe to.")
    p.add_argument("--conf", type=float, default=0.25,
                   help="Confidence threshold for counting a detection.")
    p.add_argument("--classes", default="all",
                   help="Comma-separated class NAMES that count as 'the drone' "
                        "(case-insensitive), or 'all' to count any detection. With a dedicated "
                        "drone model use 'all'; with COCO try 'airplane,bird,kite' to see "
                        "what it mistakes the drone for.")
    p.add_argument("--frames", type=int, default=200,
                   help="Number of frames to analyse, then print the verdict and exit.")
    p.add_argument("--save-dir", default=None,
                   help="If set, save annotated frames here so you can eyeball what fired.")
    return p.parse_args(argv)


def image_to_bgr(msg: Image) -> np.ndarray:
    """Convert a sensor_msgs/Image (rgb8) to an HxWx3 BGR uint8 array for Ultralytics.

    Ultralytics treats numpy inputs as BGR (OpenCV convention); the topic is RGB, so we
    reverse the channel axis. Handles row padding via msg.step.
    """
    if msg.encoding not in ("rgb8", "bgr8"):
        raise ValueError(f"expected rgb8/bgr8, got {msg.encoding!r}")
    buf = np.frombuffer(msg.data, dtype=np.uint8)
    row = buf.reshape(msg.height, msg.step)          # account for any step padding
    rgb = row[:, : msg.width * 3].reshape(msg.height, msg.width, 3)
    if msg.encoding == "rgb8":
        return rgb[:, :, ::-1]                        # RGB -> BGR
    return rgb


class StaticCamDetector(Node):
    def __init__(self, args, model):
        super().__init__("static_cam_detector")
        self.args = args
        self.model = model
        self.names = model.names  # id -> class name
        self.want = None if args.classes.strip().lower() == "all" else {
            c.strip().lower() for c in args.classes.split(",") if c.strip()
        }
        self.results = []
        self.done = False
        if args.save_dir:
            import os
            os.makedirs(args.save_dir, exist_ok=True)

        # Isaac's camera publisher is best_effort; match it or we receive nothing.
        qos = QoSProfile(depth=10, reliability=ReliabilityPolicy.BEST_EFFORT,
                         history=HistoryPolicy.KEEP_LAST)
        self.sub = self.create_subscription(Image, args.topic, self.on_image, qos)
        self.get_logger().info(
            f"listening on {args.topic}; weights={args.weights}; "
            f"classes={'all' if self.want is None else sorted(self.want)}; "
            f"conf>={args.conf}; target {args.frames} frames")

    def _class_matches(self, cls_id) -> bool:
        if self.want is None:
            return True
        return self.names.get(int(cls_id), "").lower() in self.want

    def on_image(self, msg: Image):
        if self.done:
            return
        try:
            frame = image_to_bgr(msg)
        except ValueError as e:
            self.get_logger().warn(str(e))
            return

        res = self.model.predict(frame, conf=self.args.conf, verbose=False)[0]
        best = 0.0
        for box in res.boxes:
            conf = float(box.conf[0])
            if conf >= self.args.conf and self._class_matches(box.cls[0]):
                best = max(best, conf)

        self.results.append(FrameResult(detected=best > 0.0, confidence=best))
        n = len(self.results)

        if self.args.save_dir and (best > 0.0 or n % 20 == 0):
            annotated = res.plot()  # BGR image with boxes drawn
            _save_png(f"{self.args.save_dir}/frame_{n:04d}.png", annotated)

        if n % 20 == 0:
            hits = sum(1 for r in self.results if r.detected)
            self.get_logger().info(f"frame {n}/{self.args.frames}  detections so far: {hits}")

        if n >= self.args.frames:
            self.done = True


def _save_png(path, bgr):
    """Save a BGR uint8 array as PNG without a hard OpenCV dependency at import time."""
    try:
        import cv2
        cv2.imwrite(path, bgr)
    except Exception:
        from PIL import Image as PILImage
        PILImage.fromarray(bgr[:, :, ::-1]).save(path)  # BGR -> RGB for PIL


def main(argv=None):
    args = parse_args(argv)
    from ultralytics import YOLO  # heavy import; do it after arg parsing
    model = YOLO(args.weights)

    rclpy.init()
    node = StaticCamDetector(args, model)
    try:
        while rclpy.ok() and not node.done:
            rclpy.spin_once(node, timeout_sec=1.0)
    except KeyboardInterrupt:
        pass
    finally:
        summary = summarize(node.results)
        print(format_summary(summary), flush=True)
        node.destroy_node()
        rclpy.shutdown()

    # Exit code encodes the verdict for scripting: 0 = detected at all, 1 = never.
    return 0 if summary.detected_frames > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
