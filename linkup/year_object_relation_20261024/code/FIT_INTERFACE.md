# Fixed year-object trainer interface

`fit_year_object.py` derives from the retained, never-executed contextual-role draft.
It consumes only the marked frozen `model_input` text as model features.

```
/public/software/apps/DeepLearning/PyTorch_Lib/llama_py38/bin/python3.8 fit_year_object.py \
  --inputs FROZEN_PREPARATION_DIRECTORY \
  --model-dir PINNED_LOCAL_CHECKPOINT_DIRECTORY \
  --model-manifest PINNED_CHECKPOINT_MANIFEST_JSON \
  --output NEW_PRIVATE_ATTEMPT_DIRECTORY
```

Scheduled SCNet execution requires `SLURM_JOB_ID`, one working HIP GPU, and the
already installed PyTorch/transformers stack. No package install or weight
network access is performed. Root owns model staging, support decision,
scheduler resources, submission, and the single-attempt execution lock.

The checkpoint manifest is `{"repo_id":"FacebookAI/xlm-roberta-base",
"revision":"<40 lowercase hex commit>","files":{"<relative filename>":
"<SHA256>",...}}`; its file inventory must match the local model directory exactly.

Inputs follow `INPUT_BINDING_CONTRACT.md`; all seven emitted files plus the
preparation receipt are hashed, including the held-out EVAL file. Every original
dictionary class remains in classifier outputs and fixed-class macro metrics.
Original same-item accepted masks, supervision associations and context
membership are rechecked. No final or legacy-held-out candidate enters fit.

Configuration is fixed: seed1729, three epochs, AdamW2e-5/weight decay0.01,
batch4, accumulation8, FP32, length256, YEAR markers, final epoch only. Every
frozen candidate receives a private prediction; compatible conditional metrics
are separate by original split, Pro reference GA/GB/other/unknown groups, and
frozen GenAI/software mention groups. Accepted context masks/groups must be
present and consistent in the preparation files.
Original not_stated, unmatched, ambiguous, conflicting, and unlabeled inventories
are retained. A separate conservative inventory diagnostic divides verified
one-to-one correct links by ALL frozen predictions and ALL original explicit
numeric references within accepted year/object-mask contexts. Unconfirmed
predictions remain unconfirmed; they are never declared false positives.
Strict context joint inventory-match samplecounts are also reported.
Both primary old-experience-candidate and global numeric-candidate inventories
are reported separately; both use ALL original explicit numeric references as
the recall denominator. The primary flag affects only diagnostic prediction
counts; compatible fitting and global prediction sidecars stay unchanged.
No no_relation gold, negative construction, end-to-end quality
qualification, full-chain accuracy, model selection, or automatic rerun exists.

Output creation is atomic and refuses an existing directory. The sole final
checkpoint is persisted before prediction. A training failure preserves current
private weights best effort under FAILED_PARTIAL_MODEL_PRIVATE, explicitly
ineligible for selection or automatic resume. This artifact does not contain
optimizer/RNG/cursor state and cannot support an exact training resume. Root
controls any separately authorized recovery. Failures retain original traces and a
sanitized receipt. Public results contain aggregate counts/metrics and digests;
row predictions, model artifacts, paths and original traces remain private.

Local validation is syntax compilation only; actual runtime, data checks,
training and evaluation must occur in the one scheduled attempt.
