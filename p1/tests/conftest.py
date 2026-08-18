"""Put p1/t2_free on sys.path so tests import the pipeline module directly.

Importing build_nport_convexp must stay side-effect free: its run log is a
committed provenance artifact (recover_denominators.py parses it), so the
FileHandler that opens it in mode="w" lives in _setup_run(), not at import.
"""
import sys, pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "t2_free"))
