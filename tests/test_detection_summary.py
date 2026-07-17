"""Host-side tests for the detection-summary verdict logic (no ROS/YOLO needed)."""
import pytest

from detect.detection_summary import (
    DetectionSummary,
    FrameResult,
    format_summary,
    summarize,
)


def _frames(confidences):
    """Build FrameResults from confidences; detected == confidence > 0."""
    return [FrameResult(detected=c > 0.0, confidence=c) for c in confidences]


def test_no_frames_gives_no_frames_verdict():
    s = summarize([])
    assert s.verdict == "NO_FRAMES"
    assert s.frames == 0
    assert s.detection_rate == 0.0


def test_all_frames_detect_is_detected():
    s = summarize(_frames([0.9, 0.8, 0.85, 0.92]))
    assert s.verdict == "DETECTED"
    assert s.detection_rate == pytest.approx(1.0)
    assert s.max_confidence == pytest.approx(0.92)
    assert s.mean_confidence_when_detected == pytest.approx((0.9 + 0.8 + 0.85 + 0.92) / 4)


def test_half_detection_hits_detected_threshold():
    # exactly 50% -> DETECTED (>= boundary).
    s = summarize(_frames([0.7, 0.0, 0.6, 0.0]))
    assert s.detection_rate == pytest.approx(0.5)
    assert s.verdict == "DETECTED"


def test_sparse_detection_is_intermittent():
    confs = [0.0] * 9 + [0.6]  # 10% detection
    s = summarize(_frames(confs))
    assert s.detection_rate == pytest.approx(0.1)
    assert s.verdict == "INTERMITTENT"


def test_no_detections_is_not_detected():
    s = summarize(_frames([0.0] * 20))
    assert s.verdict == "NOT_DETECTED"
    assert s.max_confidence == 0.0
    assert s.mean_confidence_when_detected == 0.0


def test_below_weak_rate_is_not_detected():
    confs = [0.0] * 99 + [0.5]  # 1% detection, below the 10% weak floor
    s = summarize(_frames(confs))
    assert s.verdict == "NOT_DETECTED"


def test_format_summary_contains_verdict_and_rate():
    s = summarize(_frames([0.9, 0.9]))
    text = format_summary(s)
    assert "VERDICT" in text
    assert "DETECTED" in text
    assert "100.0%" in text


def test_summary_is_immutable():
    s = summarize(_frames([0.9]))
    assert isinstance(s, DetectionSummary)
    with pytest.raises(Exception):
        s.verdict = "changed"  # frozen dataclass
