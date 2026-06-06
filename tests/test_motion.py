from motion import MotionEngine


def test_still_room_gives_zero_motion():
    eng = MotionEngine(window_size=5, smoothing=0.0)
    out = None
    for _ in range(5):
        out = eng.update([5.0, 0.0, 10.0, 13.0])  # identical packets
    assert out["motion_raw"] == 0.0
    assert out["motion"] == 0.0


def test_movement_raises_raw_motion():
    eng = MotionEngine(window_size=2, smoothing=0.0)
    eng.update([0.0, 0.0, 0.0, 0.0])
    out = eng.update([10.0, 10.0, 10.0, 10.0])
    # per-subcarrier population std over [0,10] is 5.0; mean across subcarriers = 5.0
    assert out["motion_raw"] == 5.0


def test_motion_is_normalized_0_to_1():
    eng = MotionEngine(window_size=2, smoothing=0.0)
    eng.update([0.0, 0.0])
    out = eng.update([10.0, 10.0])  # first real movement defines the peak
    assert out["motion"] == 1.0


def test_first_packet_is_safe():
    eng = MotionEngine(window_size=5, smoothing=0.0)
    out = eng.update([1.0, 2.0, 3.0])
    assert out["motion_raw"] == 0.0
    assert out["motion"] == 0.0


def test_set_params_updates_window():
    eng = MotionEngine(window_size=5, smoothing=0.3)
    eng.set_params(window_size=10, smoothing=0.5)
    assert eng.window_size == 10
    assert eng.smoothing == 0.5
