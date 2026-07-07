"""Put the package parent (shared/) and this tests dir on sys.path so the toy-data
tests can `import econlib` and `import toydata` no matter where pytest is invoked."""
import sys, pathlib

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))                 # toydata.py
sys.path.insert(0, str(HERE.parents[1]))      # shared/  -> `import econlib`
