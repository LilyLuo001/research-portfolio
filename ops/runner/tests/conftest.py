"""Put ops/runner on sys.path so tests can `import budget` / `import runner`."""
import sys, pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))   # ops/runner/
