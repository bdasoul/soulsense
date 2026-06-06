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


def test_energy_rises_with_strong_signal():
    eng = MotionEngine(window_size=2, smoothing=0.0)
    eng.update([1.0, 1.0])        # low energy baseline
    out_low = eng.update([1.0, 1.0])
    eng2 = MotionEngine(window_size=2, smoothing=0.0)
    eng2.update([1.0, 1.0])
    out_high = eng2.update([100.0, 100.0])   # high energy
    assert out_high["energy"] >= out_low["energy"]


def test_spread_is_between_0_and_1():
    eng = MotionEngine(window_size=3, smoothing=0.0)
    for _ in range(3):
        out = eng.update([1.0, 5.0, 2.0, 8.0, 3.0])
    assert 0.0 <= out["spread"] <= 1.0


def test_velocity_detects_sudden_change():
    eng = MotionEngine(window_size=2, smoothing=0.0)
    eng.update([5.0, 5.0])
    eng.update([5.0, 5.0])   # stable — velocity near 0
    out_stable = eng.update([5.0, 5.0])
    eng2 = MotionEngine(window_size=2, smoothing=0.0)
    eng2.update([0.0, 0.0])
    eng2.update([10.0, 10.0])
    out_burst = eng2.update([0.0, 0.0])   # sudden drop — high velocity
    assert out_burst["velocity"] >= out_stable["velocity"]


def test_set_params_affects_behavior():
    # Fill a window=2 engine with movement so motion > 0
    eng = MotionEngine(window_size=2, smoothing=0.0)
    eng.update([0.0, 0.0])
    eng.update([10.0, 10.0])
    # Resize to window=10; the 2 existing packets are preserved so motion stays > 0
    eng.set_params(window_size=10, smoothing=0.0)
    assert eng.window_size == 10
    assert eng.smoothing == 0.0
    # Next packet: window now has [10,10] plus new [0,0] — still detects motion
    out = eng.update([0.0, 0.0])
    assert out["motion_raw"] > 0.0
