# DAX Execution Plan — Amendment v1.1

Applies to *DAX Project Execution Plan with Delegated AI Agents*. Delta document; unmentioned sections stand. Motivations: (1) four research-design additions from external review (measurement-error treatment, δ calibration, decoupled index release, vintage-feasibility gate); (2) budget-constrained model-tier remapping (Claude Pro subscription + ¥300–500/month API; see `Agent_Architecture_24x7.md` §4).

---

## Amendment 1 — Measurement error in π is a named workstream, not an afterthought

Noise in the O*NET-task→π mapping propagates **nonlinearly** through the crossing indicator: threshold rules convert continuous noise into misclassified crossing *dates*, which then attenuate (or, with correlated errors, bias) the dose-response estimates. Two additions:

**1a. Errors-in-variables sensitivity module (add to W5, deliverable feeds W6 Readout 1).** Append to the Index Construction Agent prompt:

```
9. EIV sensitivity: for each mapping, perturb π with noise calibrated to the
   observed human-validation disagreement rates (from the Mapping Agent's
   inter-rater stats) and to item-level score dispersion; re-derive crossing
   dates over [N] draws; report (a) the distribution of crossing-date shifts
   per occupation-event, (b) the share of ΔDAX(o,event) cells whose dose bin
   changes, (c) implied attenuation factors for a linear dose response.
   These are pre-registered diagnostics: file the acceptable bounds in the
   memo (W1) before outcome work.
```

**1b. Cross-mapping IV specification (add to W8; pre-register in W1 memo §7).** The three mappings are built anyway; independent measurement errors across them permit the classical measurement-error IV: instrument the GDPval-based dose with the Tolan- and Eloundou-based doses. Append to the Econometrics Agent prompt:

```
9. Measurement-error IV: as a pre-registered secondary specification,
   instrument the primary (GDPval) ΔDAX dose with the Tolan and Eloundou
   doses (separately and jointly); report first-stage F, the IV/OLS ratio as
   an implied reliability estimate, and the identifying assumption
   (independent mapping errors) with its stated limitation (common structural
   errors — e.g., all three mistaking benchmark for real-task success — are
   NOT purged; say so verbatim in output).
```

Add to the Design Memo Agent prompt (W1), section 7: "Include the EIV diagnostic bounds and the cross-mapping IV as filed secondary specifications."

---

## Amendment 2 — Calibrate δ from the first stage instead of assuming it

δ ∈ {1.0, 0.8, 0.6} is currently a free parameter. Once first-stage usage data exists, δ can be *estimated*: the observed usage-share jump at crossings, relative to the jump implied under full deployment, identifies a deployment-friction factor. This converts DAX's most arbitrary assumption into a measured object — a genuine differentiator over static indices.

**Add to W1 memo (pre-registered intention, no number committed):** "Post-first-stage, a calibrated δ̂ will be derived from the ratio of observed to predicted usage-share jumps at crossing events, per the formula filed here; DAX-v1.1 will add δ̂ as a fourth grid point. The grid {1.0, 0.8, 0.6} remains the pre-registered primary for all outcome analysis in this paper."

**Add to the First-Stage Agent prompt (W7):**

```
5. δ-calibration module: from the synthetic (later real) usage aggregates,
   estimate the deployment-friction factor as filed in the memo; output
   δ̂ with a bootstrap interval, flagged clearly as post-hoc calibration
   for DAX-v1.1, not for this paper's outcome analysis.
```

---

## Amendment 3 — Decouple the public index release from the paper (split W10)

The citation race in this space is on the **index artifact**, against static incumbents (Felten/Eloundou/Webb) and live competitors (Anthropic Economic Index–style products, Chatterji et al. follow-ons). Waiting until Month 12 to release surrenders the first-mover position the whole design pays for.

**New W10a — DAX-v1 Public Release (Month 4–5, immediately after Gate 2 passes):** package = index panel (all mappings × cost variants × δ, f-grid summaries), crossing chronology, codebook, mapping protocol, construction code, versioning policy. Explicitly **excludes**: outcome analysis, first-stage results, anything NDA-adjacent. Run the CI NDA check as a release blocker. Writing & Release Agent executes with the W10 prompt's item 3 scoped to this package; PI signs.

**W10b (Months 9–12)** = paper, policy brief, replication package, as originally specified. Schedule table row for Month 4–5 gains "W10a public index release" contingent on Gate 2.

Risk note filed with the release: monthly index updates create a maintenance commitment; the versioning policy must state the update SLA you can actually sustain (recommend: monthly best-effort, guaranteed at model-release/price-change events only).

---

## Amendment 4 — Week-1 feasibility gate on vintages and GDPval access

W4 is budgeted as a cost risk but it is first a *feasibility* risk: retired OpenAI vintages are genuinely hard to access, and open-weight "reconstructions" are a predictable referee target. GDPval open-subset licensing must also be confirmed before the mapping protocol is designed around it.

**New W0.5 (Week 1, human + Chief-of-Staff agent, one afternoon):** produce `memo/feasibility_note.md` covering: (a) which registry vintages are API-accessible today, at what price, with sources; (b) which require reconstruction, which open-weight models are the filed stand-ins, and the fidelity caveat wording that will appear in the paper; (c) GDPval open-subset license terms and redistribution constraints; (d) a W4 budget ceiling given (a)–(c). **Gate rule: W3's Mapping A protocol and all W4 spend are blocked until this note is PI-signed.** If (a)–(b) leave fewer than [minimum viable] measurable vintages, the memo's event registry is trimmed *before* pre-registration rather than after.

---

## Amendment 5 — Model-tier remapping under the budget constraint

Original tiers assumed metered flagship API access. New principle (details in `Agent_Architecture_24x7.md` §4): **all Anthropic-side work runs inside the Claude Pro subscription (Claude Code with Sonnet as workhorse; claude.ai Projects for memo/spec/writing sessions); OpenAI o-series/GPT-flagship API assignments are withdrawn; cross-vendor independence is carried by budget reasoning models.**

| Role | v1.0 tier | v1.1 assignment |
|---|---|---|
| A0 Chief-of-Staff | T1 persistent | Deterministic task-graph scripts + cheap-model checklist checks; T1-level judgment only at gates, via claude.ai session |
| A2 Design Memo | T1 (Opus-class) | claude.ai Project session (Pro); DeepSeek reasoning as independent cross-read before PI sign-off |
| A4 Mapping / A6 Audit | T1 | claude.ai session for protocol + adjudication; audit sample split DeepSeek-reasoning + Gemini free tier (cross-vendor) |
| A5 Bulk Annotation | T3 (Haiku/4o-mini) | Qwen-Flash/GLM-tier (cheapest adequate); frozen rubric unchanged; audit rate raised to 10% to offset the cheaper annotator |
| A8/A10/A12 (T2 coding) | Sonnet in Claude Code | Unchanged — scheduled in daily Pro prime blocks |
| A11 Econometrics spec | T1 | claude.ai session (spec) + DeepSeek reasoning blind cross-check; PI reviews every spec (unchanged) |
| A13 Writing | T1 | claude.ai Project sessions, section-by-section |
| A14 Replication | T2 | Deterministic Makefile replay (needs no LLM except failure triage) |

**Honest trade-off:** spec review and audit quality drop roughly one tier versus Opus/o-series flagships. Compensations: (i) the governance architecture (pre-registration gates, deviation memos, replication blocking) was designed to be robust to imperfect agents — it now does more of the work; (ii) the 5–10% audit sample rises to 10% flat; (iii) the one irreplaceable T1 consumer is W1 memo quality — schedule it across multiple claude.ai sessions with PI iteration rather than one shot. The **capability panel measurement (W4) is unaffected by agent economics by construction** (pinned vintages are the measured objects); its API spend is *project data cost*, not agent cost, and is governed by the W0.5 feasibility ceiling — flag to the funder/Exchange that this line item cannot fit inside ¥500/month and needs its own budget.
