# Methods map for paper drafting

The source archive is organized by the questions a methods section must answer.

| Paper question | Snapshot evidence |
| --- | --- |
| What was treated as the analysis record? | `research_contract_v1/common_measurement.json` and `COMMON_MEASUREMENT.md` |
| Which time concept was used? | `research_contract_v1/TEXT_TIME_DECISION.md` and `stage_c_v2/TEMPORAL_JOIN_CONTRACT.json` |
| How were records sampled and parsed? | `stage_c/prepare_sample.py`, `extract_sample.py`, and `requirement_candidates.py` |
| How were support tables checked? | `stage_c_v2/support_audit.py` and aggregate files under `stage_c_v2/results/` |
| How did parsing rules change? | Versioned implementations under `stage_c_v3/`, `stage_c_v4/`, and `stage_c_v5/`; see their decisions and release gates |
| How was portability assessed? | `check_portability.py` and cross-region validation reports in v3/v4 |
| How were large runs bounded? | `stage_c_batch_v1/bounded_candidate_batch.py`, batch config, and bounded receipts |
| How were candidate outputs compacted? | Compact v1 measured cluster evidence and limitations; Compact v2 active code plus local aggregate validation |
| How was the annotation frame designed? | `stage_c_evaluation_v2/evaluation_contract.json`, codebook, frame code, and aggregate coverage/grouping reports |
| What semantic evidence exists? | Aggregate 32-record primary and fixed 8-record independent-model diagnostics; model references only, with no human-accuracy or release claim |
| How were final baselines aggregated? | `stage_d_baseline_v1/build_occupation_baseline.py` and aggregate summaries |
| Which variables may be claimed? | `research_contract_v1/VARIABLE_RELEASE_REGISTER.json` |

When drafting, describe model review as diagnostic only. The snapshot contains
no completed human annotation, so accuracy claims that require human labels are
outside the available evidence. Report the exact parser/version and contract
used for each table because the version directories represent substantive rule
changes rather than Git-era milestones.
