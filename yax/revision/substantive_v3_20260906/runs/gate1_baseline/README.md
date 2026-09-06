# Gate 1 baseline run transfer

This directory is the sanitized repository copy of the successful fresh SCC
reconstruction executed from clean Git commit `ffdac61e47fa802cabf2485ba495acae092a0fdf`.
The canonical specification is
`yaxspec_v1_83bb387f9fc28e2655db5101c7697989510475027d1dd5a9c361c797ed3925c3`.

`EXECUTION_RECEIPT.json` is the wrapper's sanitized, authenticated receipt.
The public `results/` directory contains all sixteen non-sensitive numerical
outputs in the wrapper manifest. The original R3 runner receipt is deliberately
excluded because it records private absolute SCC paths. It remains retained in
the authorized run root with SHA-256
`f72fb19deca62013ef25b97677cce702b13b3830fe6e7d64eab04e146f474301`,
and the sanitized wrapper receipt authenticates that hash and the original
output manifest. `audit_logs/` contains the six sanitized logs/failure objects
hashed by the wrapper plus a duplicate of the wrapper receipt.

The first successful execution from commit `82c73a5` is retained on SCC as an
engineering predecessor. It produced identical scientific coefficient and
uncertainty outputs, but its result identifiers used a noncanonical selector
encoding. No result was registered from that run. The wrapper was corrected,
tested, committed, and executed once more without changing the scientific
contract; this directory contains only the later authoritative run.

Validate this transfer with:

```sh
python3 yax/revision/substantive_v3_20260906/gate1_baseline/validate_public_transfer.py \
  --run-dir yax/revision/substantive_v3_20260906/runs/gate1_baseline \
  --report yax/revision/substantive_v3_20260906/gates/GATE1_BASELINE_TRANSFER_VALIDATION.json
```

This establishes reconstruction and transfer integrity. It does not establish
finite-optimum existence for every central specification; N01--N03 remain the
separate blocking numerical audit.
