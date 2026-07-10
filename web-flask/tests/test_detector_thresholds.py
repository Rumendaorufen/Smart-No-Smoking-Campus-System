from app.core.detector import SmokingDetector


def test_candidate_and_trigger_thresholds_are_aligned():
    assert SmokingDetector.SMOKE_CONFIDENCE == 0.40
    assert SmokingDetector.TRIGGER_CONFIDENCE == 0.40


def test_immediate_confirmation_remains_stricter_than_trigger():
    assert SmokingDetector.CONFIRM_CONFIDENCE == 0.60
    assert SmokingDetector.CONFIRM_CONFIDENCE > SmokingDetector.TRIGGER_CONFIDENCE
