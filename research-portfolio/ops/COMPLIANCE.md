# Compliance boundary (read before wiring anything)

The single rule that keeps this architecture on the right side of Anthropic's
terms: **the runner never holds a Claude credential, and no Claude subscription
is ever driven programmatically.**

Why this matters, from the current (2026) enforcement picture:
- Holding several *separate* Pro accounts, each used by you in the official apps,
  is not in itself a terms violation.
- What *does* get accounts flagged/suspended: sharing one login across people;
  reselling; and — most relevant here — **routing subscription work through
  third-party tools/automation harnesses** (using the subscription's OAuth token
  outside the official Claude.ai / Claude Code / Cowork apps). Coordinated
  multi-account use aimed purely at *evading rate limits* can also be read as
  limit evasion.
- Anthropic's stated position is that subscriptions cover use *inside* Claude.ai,
  Claude Code, and Cowork; continuous/production/automation workloads belong on
  the **API under Commercial Terms (pay-as-you-go)**.

So this system splits cleanly in two:
1. **L0 backbone + L1 cheap models (24/7):** your own scripts + non-Anthropic
   APIs under *their* commercial terms. Runs continuously. No Claude token.
2. **L2 Claude seats (human-driven, business hours):** you sit down at the
   official Claude Code / claude.ai app on the owning account, pull a prepared
   brief, work a block, commit. The runner PREPARES briefs; it does not execute
   them for you.

If you genuinely need always-on, programmatic Claude horsepower, put that on the
Anthropic API (commercial terms) as its own budget line — do not wire a Pro seat
into the runner.

Please confirm the specifics against Anthropic's current Usage Policy and
Consumer Terms before you buy seats; policy changes, and this note is a summary,
not legal advice.
