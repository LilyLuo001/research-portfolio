"""Put e2/ on sys.path so tests can import build_panel / assert_panel directly."""
import sys, pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))   # e2/
