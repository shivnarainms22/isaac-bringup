"""Run the drone detector on static image FILES and report per-image results.

This is the reliable validation path: instead of fighting headless-sim lighting on the Iris
mesh, run the public drone model on REAL drone photos (e.g. from below / against sky, the
checkpoint-camera view). No ROS, no sim -- just Ultralytics on image files. Saves annotated
copies so the detections can be eyeballed, and prints a per-image + overall summary.

Usage (laptop or the droneranger-detect container):
  python3 detect/detect_images.py --weights detect/weights/drone.pt --images-dir real_drones --out real_drones_annotated
"""
import argparse
import sys
from pathlib import Path

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--weights", default="detect/weights/drone.pt", help="Ultralytics YOLO weights.")
    p.add_argument("--images-dir", required=True, help="Directory of images to run detection on.")
    p.add_argument("--out", default=None, help="Directory to save annotated images (optional).")
    p.add_argument("--conf", type=float, default=0.25, help="Confidence threshold for a hit.")
    return p.parse_args(argv)


def list_images(images_dir):
    d = Path(images_dir)
    if not d.is_dir():
        raise SystemExit(f"not a directory: {images_dir}")
    files = sorted(f for f in d.iterdir() if f.suffix.lower() in IMAGE_EXTS)
    if not files:
        raise SystemExit(f"no images found in {images_dir}")
    return files


def main(argv=None):
    args = parse_args(argv)
    from ultralytics import YOLO
    model = YOLO(args.weights)
    print(f"model classes: {dict(model.names)}", flush=True)

    out_dir = Path(args.out) if args.out else None
    if out_dir:
        out_dir.mkdir(parents=True, exist_ok=True)

    files = list_images(args.images_dir)
    hits = 0
    print(f"\n{'image':40s} {'best_conf':>9s}  detections", flush=True)
    print("-" * 70, flush=True)
    for f in files:
        res = model.predict(str(f), conf=args.conf, verbose=False)[0]
        confs = [float(b.conf[0]) for b in res.boxes]
        best = max(confs, default=0.0)
        detected = best >= args.conf
        hits += 1 if detected else 0
        mark = "OK " if detected else "-- "
        print(f"{mark}{f.name:37s} {best:9.3f}  {len(res.boxes)} box(es)", flush=True)
        if out_dir:
            _save(out_dir / f"det_{f.name}", res.plot())

    n = len(files)
    print("-" * 70, flush=True)
    print(f"detected in {hits}/{n} images ({hits / n:.0%}) at conf>={args.conf}", flush=True)
    return 0 if hits > 0 else 1


def _save(path, bgr):
    try:
        import cv2
        cv2.imwrite(str(path), bgr)
    except Exception:
        from PIL import Image as PILImage
        PILImage.fromarray(bgr[:, :, ::-1]).save(str(path))


if __name__ == "__main__":
    sys.exit(main())
