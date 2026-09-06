# Reproducibility workflow for the referee revision

The original v1.1 design and confirmatory outputs remain immutable at tags `v1.1-design-freeze` and `v1.1-confirmatory-results`. All files below are post-outcome revision artifacts unless they reproduce a frozen result.

## Order of execution

1. `python yax/revision/referee_20260905/run_referee_core.py ...`
2. `python yax/revision/referee_20260905/run_referee_cells.py ...`
3. `python yax/revision/referee_20260905/run_sample_flow.py ...`
4. `python yax/revision/referee_20260905/run_referee_mobility.py ...`
5. `python yax/revision/referee_20260905/run_external_architectures.py ...`
6. `python yax/revision/referee_20260905/run_inference_audit.py ...`
7. `python paper/scripts/render_referee_revision_figures.py`
8. `make -C paper revised`

The SCC wrappers `scc_core_rerun.sh` and `scc_sample_flow.sh` record the private-data paths and project environment used for the final core and sample-flow builds. They contain no credentials. Raw IPUMS microdata remain outside git; receipts store SHA-256 hashes and aggregate counts. The public external sources are hashed in `results/external/EXTERNAL_ARCHITECTURE_RECEIPT.json`.

## Frozen and revised inputs

- Frozen design commit: `22fbf7924809b7a535e31ae0ab68f5b113ce8078`
- Frozen confirmatory-results commit: `b16109482c3bf5ca176f6f08976e120b04769945`
- Original wide CPS SHA-256: `3fe42477e6f2ce401e85123f0e278e758595c1c4071a8743f243a92752db38c9`
- March-basic repair SHA-256: `a4ae2ef06d66a0d47359ccceffff9a15843ac501a9f25f9a05aa8fdca9c4f911`
- Occupation bridge SHA-256: `0bd2f63c72e24bed2cc1cb414395c3cbddf7c00011e47ec1c1de6ae534fd1dcc`
- Exposure lookup SHA-256: `c6eb70623ea598bfc41f2352391add7a342a8809a4e57b02f2af0e75dd0223f8`
- Computerization file SHA-256: `352cb40834ec83225f747d316eb3e03fce1d1c5c65d80720c558177f85801fdd`

Seeds and draw counts are recorded row-by-row in results and receipts. The main paired comparisons use common occupation-level Rademacher multipliers so covariance is preserved. Counts reported after pre-2020 route expansion are explicitly called respondent-equivalent rather than unique respondents.
