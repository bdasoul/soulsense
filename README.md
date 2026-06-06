# SOULSENSE

Live visualization of ESP32 Wi-Fi CSI motion sensing. Reads the `CSI_DATA`
serial stream from the AP board, computes a normalized room-motion value, and
shows it in the browser as a motion meter + CSI waterfall.

## Run (live)
./.venv/bin/python soulsense.py --port /dev/cu.wchusbserial1120
Then open http://localhost:8000

## Run (replay, no hardware)
./.venv/bin/python soulsense.py --replay captures/example_csi.csv

## Test
./.venv/bin/pytest -v

Design spec: vault `/specs/2026-06-06-soulsense-design.md`
