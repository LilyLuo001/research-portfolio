# Early retained-history audit: messages 0064–0855

Audit scope: `private_history/02_sep24_through_sep27.txt` and `private_history/03_sep28_through_oct02.txt`. I read all 792 retained message blocks: 532 messages `[0064]`–`[0595]` in phase 02 and 260 messages `[0596]`–`[0855]` in phase 03. The source history remains private and was not copied into Git. This report omits credentials, raw advertisement text, private IDs, and row outputs.

## Original aims and changes

The initial aim was to obtain the authorized Dewey data, beginning with LinkUp and then checking Revelio/other authorized sources. The user asked for all available data, Parquet where possible, direct download to SCNet, and model delegation. Messages `[0065]`, `[0068]`, `[0071]`, and `[0076]` establish the broad request and the initial LinkUp inventory: 13 tables across Job Records, Reference Tables, and Analytics. The early operational change was from a single immediate project folder to a staged download plan because most tables were authorized but not yet added to the Dewey project (`[0073]`–`[0087]`).

The first successful data path was LinkUp Job Records: the history reports 269 Parquet files and roughly 63 GB (`[0070]`), followed by successful completion and integrity checking of the initial three accessible tables (`[0096]`–`[0110]`). A later project/API path exposed the full Job Descriptions table, 2,464 files and roughly 652 GB (`[0111]`–`[0114]`). The work then split: continue long-running description transfer while independently inspecting and cleaning Job Records (`[0121]`–`[0135]`).

The research aim narrowed during early cleaning. The proposed main question became how technology change affects the role of general, occupation/industry, and tool experience in hiring, without assuming lower or higher barriers (`[0126]`, `[0826]`–`[0832]`). The data-driven design recognized that Job Records lacked a ready occupation code and that historical O*NET coverage was incomplete (`[0127]`–`[0128]`), so early outputs were limited to employer/date/region coverage and later joins rather than immediate historical occupation claims.

Phase 02 also introduced storage and execution controls. The account had a 500 GB free storage constraint despite a larger displayed allocation (`[0137]`–`[0146]`), prompting a 450 GB download pause threshold (`[0144]`). Cleaning used a separate card and bounded memory, while downloads remained isolated (`[0123]`–`[0135]`). Later work moved from local/interactive checking to scheduled, resumable cluster jobs and explicit receipts.

Phase 03 (Sep 28–Oct 2) shifted from acquisition to production recovery and publication. It contains the Wuzhen/Kunshan transfer, DCU/CPU scheduling, shard-level completion, retries, and publication races. The key transition is the report that 2,464 shards had computed but 72 still lacked transfer acceptance (`[0833]`), followed by the analysis agenda and Git transition commit (`[0834]`–`[0835]`). The research plan was deliberately preserved while an execution addendum was added (`[0836]`–`[0846]`), and the team required actual job IDs before calling analysis started (`[0847]`–`[0855]`).

## Successes versus claims only

Successes supported by retained messages and later Git receipts:

- The LinkUp Job Records download path was established, resumed after credential rotation, and early Parquet/file checks were performed (`[0096]`–`[0110]`).
- The Job Descriptions scale and format were identified before launching the long transfer (`[0111]`–`[0114]`).
- Job Records were processed independently of descriptions, with bounded memory and resumable per-file progress (`[0121]`–`[0135]`).
- Storage risk was detected and a pause threshold was introduced before the large description transfer could consume the full allocation (`[0137]`–`[0146]`).
- The operational record preserved failed tasks, retries, duplicate-shard races, and partial publication rather than silently treating them as complete (`[0787]`–`[0825]`).
- By `[0833]`, computation was complete for 2,464 shards, while transfer/publication was still incomplete; the distinction was explicitly visible before the later D65 correction.

Claims that were only provisional or later corrected:

- “All authorized data” was a requested scope, not a completed deliverable. Most LinkUp tables initially required project inclusion (`[0073]`–`[0076]`), and Revelio availability was not established in these phases.
- Progress estimates such as “50–80 minutes” (`[0082]`) and later completion forecasts were operational estimates, not final receipts.
- The early statement that three tables had completed (`[0110]`) did not establish that all 13 LinkUp tables or Job Descriptions were complete.
- “All data cleaned” was not a valid whole-corpus publication claim while 72 shards remained unaccepted for transfer (`[0826]`–`[0835]`).
- The phase-03 plan correctly warned that an analysis script being prepared was not the same as a submitted or running job (`[0831]`, `[0851]`–`[0855]`). This distinction became a core later rule.

## Constraints that were superseded or tightened

- Initial broad Dewey-wide acquisition was narrowed operationally to data actually present in the selected project and authorized download paths; inaccessible/project-unadded tables were not silently treated as downloaded (`[0068]`–`[0076]`).
- Initial root-driven/interactive control was replaced by role separation, bounded model delegation, resumable jobs, and receipts (`[0099]`–`[0100]`, `[0122]`–`[0126]`, `[0834]`).
- The assumption that a downloaded reference table could supply occupation information was corrected: the inspected Company/Ticker reference connected companies to securities, not occupations (`[0130]`–`[0136]`).
- The idea of freezing a historical employer–occupation panel was explicitly softened because time coverage and linkage validity were uncertain (`[0838]`–`[0842]`).
- Transfer and computation were separated: completed semantic computation did not imply published/accepted shards (`[0820]`–`[0825]`, `[0833]`–`[0855]`). This was later formalized in D65–D68.

## Repeated loops and contradictions

1. **Download access loop.** API keys repeatedly changed state: one was invalid, another briefly exposed a table then failed, and a later key restored continuation (`[0092]`–`[0098]`). This caused repeated permission checks and progress estimates. The durable fix was to retain partial files and use explicit table/project scope instead of inferring access from a single key response.

2. **Storage/accounting loop.** The displayed allocation was initially confused with free quota, then corrected to a 500 GB free limit and a 450 GB safety stop (`[0137]`–`[0146]`). The correction was operationally important because the description table alone was about 652 GB.

3. **Parallelism/resource loop.** The history repeatedly tested more cores, smaller tasks, alternate queues, and node retention (`[0777]`–`[0819]`). Some attempts increased scheduling complexity without reducing the underlying work. A transfer race and same-name shard collision then caused a failure and repair (`[0820]`–`[0825]`).

4. **Completion-language loop.** Several updates used “complete” for a substage while later evidence showed pending transfer/publication (`[0826]`–`[0835]`). The later execution rule requiring submitted/running/failed IDs before claiming analysis began (`[0851]`–`[0855]`) is the correct resolution.

5. **Research-scope loop.** The plan moved from all-data acquisition to a focused experience/technology question, while preserving the broader plan and refusing to infer a historical panel before time validity was established (`[0126]`–`[0128]`, `[0836]`–`[0846]`). This was a productive narrowing, but the earlier broad language remained in the conversation and could be mistaken for an active commitment.

## Why the completed base was later missed

These early files show that “2,464 shards computed” and “all data transferred/published” were already treated as different states by Sep 30 (`[0833]`–`[0835]`). The later D63/D64 rule-first work introduced a second extraction/continuation path. The historical base was missed when later remaining-shard/controller counts were interpreted as overall corpus incompleteness rather than as the status of the newer rule-first path. Git later supplies the correction: `a0ed226` published the full semantic/narrow base, and D65’s `ROOT_REUSE_DECISION.json` identifies the completed 2,464-shard extraction. The early record therefore shows a state-model problem—multiple pipelines and “complete” substage language—not evidence that the old base never existed.

## Cross-references to Git evidence

- Transition plan and first analysis agenda: [analysis_transition_20260930/NEXT_ANALYSIS_AGENDA.md](/Users/lilyluo/Documents/LinkUp_Research_20260924/reproducibility_git/linkup/analysis_transition_20260930/NEXT_ANALYSIS_AGENDA.md), [analysis_transition_20260930/README.md](/Users/lilyluo/Documents/LinkUp_Research_20260924/reproducibility_git/linkup/analysis_transition_20260930/README.md).
- Full base release: commit `a0ed226`, with the retained receipt under `analysis_transition_20260930/pre_revelio_execution_v1/results/full_semantic_narrow_v1/BATCH_RECEIPT.json` in the source history.
- Reuse correction: [reuse_audit_20261010/ROOT_REUSE_DECISION.json](/Users/lilyluo/Documents/LinkUp_Research_20260924/reproducibility_git/linkup/analysis_transition_20260930/reuse_audit_20261010/ROOT_REUSE_DECISION.json).
- Publication chronology: `6f517aa` (transition), `758687e` (D63 findings), `5330ead` (D64 adjudication), `4708284` (D65 correction), `5a1aea8` (D66), `7989998`/`232465c` (D67), `2e51035` (D68).

Coverage count: 792/792 message blocks read across the two assigned files; message ID range `[0064]`–`[0855]` with no gaps in the retained phase files.
