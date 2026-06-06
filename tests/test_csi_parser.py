import math
from csi_parser import parse_csi_line

GOOD = ("CSI_DATA,AP,3C:71:BF:6D:2A:78,-73,11,1,0,1,1,1,0,0,0,0,"
        "-93,0,1,1,80272146,0,101,0,0,80.363225,8,[3 4 0 0 6 8 5 12]")

def test_parses_core_fields():
    rec = parse_csi_line(GOOD)
    assert rec is not None
    assert rec["mac"] == "3C:71:BF:6D:2A:78"
    assert rec["rssi"] == -73
    assert rec["timestamp"] == 80.363225

def test_computes_amplitudes_from_imag_real_pairs():
    rec = parse_csi_line(GOOD)
    # pairs (imag,real): (3,4)->5, (0,0)->0, (6,8)->10, (5,12)->13
    assert rec["amplitudes"] == [5.0, 0.0, 10.0, 13.0]

def test_returns_none_for_non_csi_line():
    assert parse_csi_line("I (123) wifi: some log line") is None

def test_returns_none_for_garbage():
    assert parse_csi_line("CSI_DATA,AP,broken") is None

def test_returns_none_for_empty():
    assert parse_csi_line("") is None
