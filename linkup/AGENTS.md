# LinkUp project execution rules

User decision, 2026-10-08: all new research data processing runs in cloud/cluster jobs.

- Do not run advertisement extraction, cleaning, matching, model evaluation or analytical computations on the Mac or through conversation-model labeling agents. Agents may plan, write code, review methods and coordinate scheduled jobs.
- Local SSH/SFTP, file transport, transport checksums, code/document editing and Git are permitted control-plane work. Do not perform heavy work on cluster login nodes.
- Submit actual scheduler jobs for compute. Report their purpose and actual job IDs, queue, requested CPUs/memory/accelerators, time limits, observed states and exits. Do not call an archive verification or hardware probe a production inference job.
- Pin and record code/model/runtime versions and input/output manifests. Preserve unknowns, rejected evidence and failures. A different model runtime does not automatically inherit a prior model's measurement acceptance.
- Preserve historical execution provenance: conversation-hosted labels and Mac validations remain identified as such even after transfer to cloud. Do not rewrite history to imply cloud computation.
- After cloud transport verification, remove only explicitly inventoried active local private-data working copies and generated caches. Never delete an unverified unique artifact, original user attachment or repository history.
- Git contains code, methods, sanitized run receipts and aggregate results only. No credentials, private advertisement text, individual record IDs, raw model outputs or private sampling maps.
- Use the existing authorized SCNet resources first. Do not allocate Azure/AWS resources or resume cloud-provider investigations without a new user request. The optional future credits mentioned by the user are Azure, not AWS.
- Preserve efficient delegation: use appropriate bounded engineering tasks, root decisions and acceptance. Do not restart open-ended measurement development or reprocess finished work without a concrete correctness reason.

Authoritative correction and migration receipts are under:
`analysis_transition_20260930/dual_source_execution_v2/next_stage_20261004/cloud_execution_20261008/`.
