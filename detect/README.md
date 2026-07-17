# Static-camera ground-viewpoint YOLO experiment

**Question this answers:** a ground camera in the checkpoint network looks *up/across* at the
drone — a viewpoint the drone's own (forward/down) YOLO never trained on. Before building the
ROS checkpoint pipeline around ground cameras, we need to know: **does a detector fire on the
drone from that viewpoint at all?** This harness renders exactly that view in Isaac Sim and
runs YOLO on it — no hardware, no going outside.

## Pieces

| Part | File | What it does |
|------|------|--------------|
| Ground camera in Isaac | `isaac/bringup.py --static-cam` + `isaac/static_cam.py` | Fixed world camera aimed up at the drone → publishes `/static_cam/rgb` |
| Detector node | `detect/detect_static_cam.py` | Subscribes `/static_cam/rgb`, runs YOLO, prints a verdict |
| Verdict logic | `detect/detection_summary.py` | Aggregates per-frame hits → DETECTED / INTERMITTENT / NOT_DETECTED |
| Detect container | `detect/Dockerfile` + `scripts/setup_detect.sh` | ros:jazzy + Ultralytics YOLO |
| Runner | `scripts/run_detect.sh` | One command to run the detector against the live stream |

## Run it (on the GPU box)

Pull the repo first: `git -C ~/isaac-bringup pull`

**1. Build the detector image once (needs internet):**
```
bash ~/isaac-bringup/scripts/setup_detect.sh
```

**2. Start the sim WITH the ground camera** (adds `--static-cam` to the normal session):
```
STATIC_CAM=1 bash ~/isaac-bringup/scripts/run_session.sh start
```
Confirm the ground camera came up:
```
bash ~/isaac-bringup/scripts/run_session.sh status
```
You want a line like `static ground camera attached: /static_cam/rgb ...`.

**3. Aim check (optional but recommended).** Grab one frame and eyeball whether the drone is
actually in view, before trusting a NOT_DETECTED:
```
docker run --rm --network=host --ipc=host -e ROS_DOMAIN_ID=0 -e RMW_IMPLEMENTATION=rmw_fastrtps_cpp -e FASTRTPS_DEFAULT_PROFILES_FILE=/work/config/fastdds_udp_only.xml -e FASTDDS_DEFAULT_PROFILES_FILE=/work/config/fastdds_udp_only.xml -v $HOME/isaac-bringup:/work ros:jazzy bash -lc "source /opt/ros/jazzy/setup.bash && python3 /work/verify/grab_frame.py /static_cam/rgb /work/static_cam_frame.png"
```
If the drone is off-frame, re-launch with a tuned aim, e.g. add to the sim launch:
`--static-cam-pos 0 -6 0.5 --static-cam-euler 55 0 0` (or edit defaults in `isaac/static_cam.py`).

**4. Run the detector.** With your project's drone weights (the real signal):
```
bash ~/isaac-bringup/scripts/run_detect.sh --weights /work/detect/weights/drone.pt --frames 200
```
Smoke test only (COCO — has no "drone" class, just proves the pipeline flows):
```
bash ~/isaac-bringup/scripts/run_detect.sh --frames 100
```
Save annotated frames to see what fired:
```
bash ~/isaac-bringup/scripts/run_detect.sh --weights /work/detect/weights/drone.pt --frames 200 --save-dir /work/detect/out
```

## Reading the verdict

```
=== STATIC-CAM DETECTION SUMMARY ===
detection rate : 78.0%
max confidence : 0.612
VERDICT        : DETECTED
```

- **DETECTED** (fires on ≥50% of frames): the ground viewpoint works — proceed to build the ROS checkpoint pipeline.
- **INTERMITTENT** (≥10%): marginal — try a closer camera, a better/ fine-tuned model, or a higher hover.
- **NOT_DETECTED** (<10%): the detector doesn't see the drone from below. This is the risk the experiment exists to surface — **before** building plumbing around it.

## Caveats (so you read the result honestly)

- The rendered drone is Pegasus's **Iris** mesh, not the project's X500. A NOT_DETECTED could be
  the sim *appearance*, not the viewpoint. Confirm the aim frame first (step 3), and treat a
  clean DETECTED as strong evidence and a NOT_DETECTED as "investigate", not "the idea is dead".
- Weights matter: COCO YOLO has no drone class. Use a drone-trained model for the real answer;
  put weights under `detect/weights/` (they mount into the container at `/work/detect/weights/`).

Weights live outside git (large); create `detect/weights/` on the box and drop your `.pt` there.
