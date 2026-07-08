"""econlib — the portfolio's shared causal-inference toolkit.

One versioned package that P1 (fund conversions), E2 (RWA looping) and DAX (AI
exposure) all import rather than re-implement. Owned by seat D; read-only to the
project seats. numpy + pandas only.

  did.twfe_did / did.callaway_santanna   staggered difference-in-differences
  did.stacked_did / did.build_stacked    per-event clean-control stacking (P1 main spec)
  eventstudy.event_study                 dynamic DiD / pre-trend test
  wildboot.wild_cluster_bootstrap        small-#-clusters inference
  ri.randomization_inference             distribution-free permutation p-values
"""
from . import ols, did, wildboot, ri, eventstudy

__all__ = ["ols", "did", "wildboot", "ri", "eventstudy"]
__version__ = "0.2.0"
