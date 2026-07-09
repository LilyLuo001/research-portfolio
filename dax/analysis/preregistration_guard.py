"""Pre-registration guard — DAX W0 requirement 2.

Every script under dax/analysis/outcomes/ MUST begin with:

    import sys, pathlib
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
    import preregistration_guard  # noqa: F401  (module-level check runs on import)

Importing this module refuses to proceed (SystemExit) unless the git tag
`v1.0-preregistered` exists — the tag GATE 1 creates when the PI signs the
design memo (docs/DAX_Execution_Plan §W1). Until then, outcome analyses are
sealed by construction (proposal §1.1).

Defense in depth — this runtime check is layer 2 of 3:
  1. CI refuses any file committed under dax/analysis/outcomes/ pre-tag
     (.github/workflows/ci.yml "outcomes stay sealed"), which is also why
     THIS module lives in dax/analysis/, not inside outcomes/.
  2. This import guard stops local/interactive execution pre-tag.
  3. The NDA grep (same CI job) blocks OpenAI-NDA aggregates repo-wide.

The guard is fail-closed: if git itself is unavailable, execution is refused.
"""
import pathlib
import subprocess
import sys

TAG = "v1.0-preregistered"
_ROOT = pathlib.Path(__file__).resolve().parents[2]


def preregistration_tag_exists():
    try:
        r = subprocess.run(
            ["git", "-C", str(_ROOT), "tag", "-l", TAG],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15)
        return TAG in r.stdout.decode().split()
    except Exception:
        return False  # fail closed


def require_preregistration():
    if not preregistration_tag_exists():
        sys.exit(
            "REFUSED: dax/analysis/outcomes/ is sealed until the git tag "
            "'{0}' exists (GATE 1: PI signs the design memo; see "
            "docs/DAX_Execution_Plan_with_AI_Agents.md §W1). "
            "Do not work around this guard.".format(TAG))


require_preregistration()
