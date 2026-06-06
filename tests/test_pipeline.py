from motion import MotionEngine
from sources import FileSource, run_pipeline


def test_file_source_yields_lines():
    src = FileSource("captures/example_csi.csv", loop=False, delay=0.0)
    lines = list(src.lines())
    assert len(lines) > 0
    assert any(l.startswith("CSI_DATA,") for l in lines)


def test_pipeline_emits_motion_messages():
    src = FileSource("captures/example_csi.csv", loop=False, delay=0.0)
    eng = MotionEngine(window_size=10, smoothing=0.3)
    messages = list(run_pipeline(src, eng))
    assert len(messages) > 0
    msg = messages[-1]
    for key in ("t", "motion", "motion_raw", "rssi", "amplitudes"):
        assert key in msg
    assert 0.0 <= msg["motion"] <= 1.0
    assert isinstance(msg["amplitudes"], list)
