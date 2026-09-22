#!/usr/bin/env python3
"""Plot the eight external-test FOMC A2-to-A5 event/control results."""
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


HERE = Path(__file__).resolve().parents[1]
src = HERE / "results" / "model_summary" / "PAIRED_EVENT_CONTROL.csv"
out = HERE / "results" / "FIGURE_PRIMARY_A2_A5_TEST.png"
d = pd.read_csv(src)
d = d[
    d["comparison"].eq("A2_TO_A5_COMPLETE_SPY_AFTER_C")
    & d["split"].eq("TEST")
    & d["window"].eq("POST_0_60S")
].copy()
d["label"] = d["event_id"].str.replace("FOMC_", "", regex=False)

fig, axes = plt.subplots(1, 2, figsize=(11, 4.2), sharey=True)
for ax, fit in zip(axes, ["OWN_LAMBDA", "FIXED_A2_LAMBDA"]):
    x = d[d["fit_spec"].eq(fit)].sort_values("event_id")
    ax.axhline(0, color="black", lw=.8)
    ax.plot(x["label"], 100 * x["equal_weight_G_event"], "o-", label="FOMC event")
    ax.plot(x["label"], 100 * x["equal_weight_G_control"], "s--", label="matched control")
    ax.set_title(fit.replace("_", " ").title())
    ax.set_xlabel("2024 FOMC date")
    ax.tick_params(axis="x", rotation=45)
    ax.grid(alpha=.2)
axes[0].set_ylabel("A2→A5 incremental G (percentage points)")
axes[-1].legend(frameon=False)
fig.suptitle("SPY's conditional one-second predictive increment is small and specification-sensitive")
fig.tight_layout()
fig.savefig(out, dpi=180)
