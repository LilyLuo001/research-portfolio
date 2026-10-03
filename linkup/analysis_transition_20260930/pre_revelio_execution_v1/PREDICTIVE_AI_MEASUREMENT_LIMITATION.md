# Predictive AI and general-work measurement limitation

Status: diagnostic only; frozen V6 and release-v1 rules were not changed.

The full narrow aggregate's zero applicant-context `predictive_ai` detections
is structural under the frozen pipeline, rather than evidence that predictive
models never occur in job requirements. Release-v1 maps the literal phrase
`predictive model(s)` to `predictive_ai` ([frozen snapshot enrichment](../../cleaning_pipeline_20260928/source_snapshot/stage_c_release_v1/enrichment.py):22), but applicant context is copied only from an overlapping upstream V6 `ai` or `software` evidence item ([frozen snapshot enrichment](../../cleaning_pipeline_20260928/source_snapshot/stage_c_release_v1/enrichment.py):76). The V6 parser does not itself emit an `ai`/`software` evidence item for the predictive-model phrase. The working project uses the equivalent frozen sources at `stage_c_v6/` and `stage_c_release_v1/`. Thus a requirement such as the synthetic string “Required: develop predictive models.” produces a predictive technology row with explicit `develop`, but `applicant_context_candidate=false`; it is removed by the narrow table's applicant-context filter.

The companion synthetic evidence test also shows that “experience with
predictive models” can receive explicit `use`, yet remains outside the
applicant-context detected count for the same reason. The reported full-frame
zero therefore cannot be interpreted as a prevalence estimate or as evidence
of no predictive-AI demand. It should be reported as unavailable under the
current applicant-context technology measure.

`general_work` is also deliberately narrow. `_object_type` assigns it only
when the extracted object is empty or exactly one of `overall`, `general`,
`professional`, or `work` after trimming ([frozen snapshot enrichment](../../cleaning_pipeline_20260928/source_snapshot/stage_c_release_v1/enrichment.py):90). Longer phrases such as “general work” and all unrecognized experience scopes fall into `object_unspecified`; the latter's 27.61% is unresolved scope, not a general-work complement. The 0.516% general-work main rate therefore reflects this full-match definition and should not be read as the rate of all broadly transferable experience.
