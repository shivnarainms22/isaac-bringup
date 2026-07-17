"""Pure aggregation of per-frame detection results -> a verdict. No ROS/YOLO deps.

The static-camera experiment asks one question: from a ground camera looking up, does the
detector recognise the drone? This module turns a stream of per-frame results into that
answer (detection rate, best/mean confidence, verdict) so the logic is unit-testable
without a GPU, ROS, or a rendered scene.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class FrameResult:
    """One frame's outcome: did the target class fire, and at what confidence.

    detected: True if the target class was present above the caller's confidence threshold.
    confidence: best confidence for the target class this frame (0.0 if not detected).
    """
    detected: bool
    confidence: float


@dataclass(frozen=True)
class DetectionSummary:
    frames: int
    detected_frames: int
    detection_rate: float   # detected_frames / frames, 0.0 if no frames
    max_confidence: float
    mean_confidence_when_detected: float
    verdict: str


# Fraction of frames that must detect for the viewpoint to count as "recognised".
DETECTED_VERDICT_RATE = 0.5
WEAK_VERDICT_RATE = 0.1


def summarize(results, detected_rate=DETECTED_VERDICT_RATE, weak_rate=WEAK_VERDICT_RATE) -> DetectionSummary:
    """Aggregate FrameResults into a DetectionSummary with a human verdict.

    Verdicts:
      DETECTED      -- fires on >= detected_rate of frames: the ground viewpoint works.
      INTERMITTENT  -- fires on >= weak_rate but < detected_rate: marginal, needs a better
                       model / closer camera / fine-tune.
      NOT_DETECTED  -- fires on < weak_rate of frames: the detector does not see the drone
                       from this viewpoint (the risk this experiment exists to surface).
    """
    frames = len(results)
    if frames == 0:
        return DetectionSummary(0, 0, 0.0, 0.0, 0.0, "NO_FRAMES")

    detected = [r for r in results if r.detected]
    detected_frames = len(detected)
    rate = detected_frames / frames
    max_conf = max((r.confidence for r in results), default=0.0)
    mean_conf = (sum(r.confidence for r in detected) / detected_frames) if detected_frames else 0.0

    if rate >= detected_rate:
        verdict = "DETECTED"
    elif rate >= weak_rate:
        verdict = "INTERMITTENT"
    else:
        verdict = "NOT_DETECTED"

    return DetectionSummary(
        frames=frames,
        detected_frames=detected_frames,
        detection_rate=rate,
        max_confidence=max_conf,
        mean_confidence_when_detected=mean_conf,
        verdict=verdict,
    )


def format_summary(s: DetectionSummary) -> str:
    """One-block human-readable report of the experiment outcome."""
    return (
        f"=== STATIC-CAM DETECTION SUMMARY ===\n"
        f"frames analysed      : {s.frames}\n"
        f"frames with detection: {s.detected_frames}\n"
        f"detection rate       : {s.detection_rate:.1%}\n"
        f"max confidence       : {s.max_confidence:.3f}\n"
        f"mean conf (detected) : {s.mean_confidence_when_detected:.3f}\n"
        f"VERDICT              : {s.verdict}"
    )
