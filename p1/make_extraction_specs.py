"""P1 — generate the four post-gate extraction batch specs from the harvested
EDGAR package (L0, deterministic, no LLM). RUN ON THE BOX — raw filings are
box-local (p1/edgar_filings/*.htm, gitignored; manifest.csv is committed).

Emits ops/l1/{P1-T1-events,P1-T1-events-B,P1-T13-ant,P1-T13-ant-B}.yaml:
  - T1 channels get filings matched by conversion-language queries;
    T13 channels get filings matched by ANT/semi-transparent queries.
  - Channel A worker = deepseek, channel B = gemini_free (kimi is benched;
    deepseek/google keeps the cross-vendor A/B constraint; extraction reads
    EMBEDDED text so neither channel needs web_search).
  - One item per filing: focused excerpts (keyword windows) rather than the
    whole prospectus; per manual §T1 every field must be locatable in the
    filing, NA otherwise, no memory.
  - Known-answer fence from repo-verified facts (docs 修订3 anchor date;
    P1-T0-crash-B owner-armed FEDS-note fence; events_from_note.csv family).

Idempotent: --force to overwrite existing specs.
"""
import argparse
import csv
import html
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PKG = os.path.join(ROOT, "p1", "edgar_filings")
L1 = os.path.join(ROOT, "ops", "l1")

ANT_MARKERS = ("activeshares", "semi-transparent", "proxy portfolio")
KEYWORDS = re.compile(r"convert|conversion|exchange-traded|semi-transparent|"
                      r"proxy portfolio|activeshares", re.I)
WINDOW, MAX_WINDOWS, HEAD = 1500, 4, 1200
TAG = re.compile(r"<[^>]+>")

T1_RULES = """【规则 v2 (manual §T1 + QC修订). Follow the STEPS in order for THIS filing's excerpt.

STEP 1 — Identify every reorganization/conversion described. For each one name:
  TARGET = the entity whose shareholders receive new shares (acquired/converted fund)
  ACQUIRER = the entity that survives (acquiring/successor fund)
STEP 2 — Classify both, quoting the excerpt:
  TARGET must be an OPEN-END MUTUAL FUND (multi-class shares, bought/redeemed at NAV).
  ACQUIRER must be an ETF (exchange-traded fund / "will operate as an exchange-traded
  fund" / listed on an exchange).
STEP 3 — Verdict:
  EVENT only if TARGET=open-end mutual fund AND ACQUIRER=ETF. This includes:
   (a) shell-ETF conversions and cross-trust reorganizations into a new ETF;
   (b) acquisition of a mutual fund by an EXISTING ETF;
   (c) RETROSPECTIVE statements of completed conversions ("the ETF is the successor
       to the X Fund as a result of a reorganization on <date>") — record the event
       with effective_date = the stated completion date.
  NOT events — output {"no_event": true, "reason": "<code>"} with code:
   MF_TO_MF   mutual fund merged into another MUTUAL FUND (acquirer not an ETF)
   ETF_TO_ETF target is itself an ETF (trust adoption/re-domiciliation/rebrand)
   CEF        target is a closed-end fund (incl. CEF→ETF: code CEF, add "flag":"CEF_to_ETF")
   INTERVAL   acquirer is an interval fund or other non-ETF structure
   SHARECLASS share-class conversion/aging (e.g. Class C→A), fund rename, no reorganization
   MENTION    ETFs appear only as portfolio holdings/risk language/ordinary prospectus text
  If the excerpt truly shows no reorganization at all, use code MENTION.

OUTPUT — one JSON value per item id. Copy the item id EXACTLY as printed after 文件:
(character-for-character; never re-type digits). Value is a PLAIN JSON object (never a
quoted/escaped string):
  {"events": [ {one object PER TARGET FUND named in the filing — enumerate ALL rows of
   the Target/Acquiring fund table, a 4-fund filing yields 4 objects}, ... ]}
  or the no_event object above.
Each event object:
  fund_name        target mutual fund's full name (from excerpt)
  family           fund family/trust (from excerpt)
  mutual_fund_ticker / etf_ticker
                   a single 2-6 char UPPERCASE symbol from the excerpt, else "NA".
                   NEVER a fund name. Multiple class tickers → "NA" and list them in evidence.
  announce_date    YYYY-MM-DD only. Board-approval date if stated; else the document's own
                   date; else the filed date. Vague ("May 2020","Q4 2026") → "NA".
  date_basis       "board" | "document" | "filed" | "NA"
  effective_date   YYYY-MM-DD only; the stated closing/completion date. Vague → "NA".
  asset_class      equity_US / equity_intl / fixed_income / other — ONLY if locatable in the
                   excerpt (bond/muni/high-yield/MBS→fixed_income; International/EM/Asia→
                   equity_intl; explicit US equity→equity_US; managed-futures/multi-asset/
                   long-short→other). Name alone insufficient → "NA".
  AUM_at_conversion_USD  number from excerpt or "NA"
  source_accession copy from the 文件 line
  confidence       H = fund identity + (announce or effective) with explicit basis;
                   M = identity clear, dates partly missing/document-dated;
                   L = identity inferred from title only
  evidence         ≤25-word quote fragment supporting the verdict (for events: the words
                   showing the acquirer is an ETF; for no_event: the words showing why not)
NEED_HUMAN only when TWO date statements INSIDE THIS ONE EXCERPT contradict for the same
fund: {"NEED_HUMAN": true, "quotes": ["...", "..."]}. Different filings never contradict.
Never fill any field from memory — excerpt-locatable or "NA".

SELF-CHECK before emitting (do this, don't print it): every input item id appears exactly
once in your answer map (count them); every event object quotes ETF-acquirer evidence;
every date matches ^\\d{4}-\\d{2}-\\d{2}$ or is "NA"; no ticker field contains a space.】"""

T13_RULES = """【规则 (修订4 T13, schema 同 T1 增两列): disclosure_regime(daily_full/
semi_transparent), proxy_basket_type。逐字段定位符; NA 不推断; 不含相关事件 →
{"no_event": true}。范围: 2019-11 以来上市或转换的半透明主动 ETF。】"""

SENTINELS = """# Known-answer fence. S1/S2 are document-grounded (synthetic excerpt,
# answer known by construction): both no-web workers failed the old trivia fence
# 2026-07-17 (S2 asked about a 2025-11 publication past model cutoffs).
# S3 keeps one repo-verified domain fact (docs/P1_修订补丁_v1_1.md 修订3).
sentinels:
  - id: S1
    prompt: "Filing excerpt: 'The Board of Trustees of Ridgeline Funds Trust approved the conversion of the Ridgeline Mid-Cap Growth Fund, a mutual fund (ticker: RMCGX), into an actively managed exchange-traded fund (ticker: RMCG), expected to become effective on or about April 22, 2022.' What is the MUTUAL FUND ticker in this excerpt? Reply with the ticker only."
    expect: "RMCGX"
  - id: S2
    prompt: "Filing excerpt: 'The Board of Trustees of Ridgeline Funds Trust approved the conversion of the Ridgeline Mid-Cap Growth Fund, a mutual fund (ticker: RMCGX), into an actively managed exchange-traded fund (ticker: RMCG), expected to become effective on or about April 22, 2022.' On what date is the conversion expected to become effective? Reply with YYYY-MM-DD only."
    expect: "2022-04-22"
  - id: S3
    prompt: "Filing excerpt: 'The Board of Trustees of Ridgeline Funds Trust approved the conversion of the Ridgeline Mid-Cap Growth Fund, a mutual fund (ticker: RMCGX), into an actively managed exchange-traded fund (ticker: RMCG), expected to become effective on or about April 22, 2022.' What is the name of the trust in this excerpt? Reply with the trust name only."
    expect: "Ridgeline Funds Trust"
"""


def excerpt(path):
    try:
        raw = io.open(path, "r", encoding="utf-8", errors="ignore").read()
    except IOError:
        return None
    text = html.unescape(TAG.sub(" ", raw))
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return None
    parts, spans = [text[:HEAD]], []
    for m in KEYWORDS.finditer(text):
        lo, hi = max(0, m.start() - WINDOW // 2), m.start() + WINDOW
        if spans and lo <= spans[-1][1]:
            spans[-1] = (spans[-1][0], hi)
        else:
            spans.append((lo, hi))
        if len(spans) >= MAX_WINDOWS:
            break
    parts += [text[lo:hi] for lo, hi in spans if lo > HEAD]
    return " […] ".join(parts)


def yaml_quote_block(s):
    return "\n".join("      " + line for line in s.splitlines())


def build_spec(task_id, worker, rules, rows, channel_note):
    lines = [
        "# {0} — generated by p1/make_extraction_specs.py from the harvested".format(task_id),
        "# EDGAR package ({0} filings; manifest.csv is the locator source).".format(len(rows)),
        "# {0}".format(channel_note),
        "# Extraction reads embedded excerpts — no web_search needed.",
        "worker: {0}".format(worker),
        "web_search: false",
        "max_items_per_call: 6",
        "est_cost: {0}".format(round(0.01 * len(rows) + 0.5, 2)),
        "items:",
    ]
    for r in rows:
        body = "{0}\n文件: {1} (form {2}, filed {3}, {4})\nsource_url: {5}\n节选:\n{6}".format(
            rules, r["accession"], r["form"], r["filed"], r["company"],
            r["source_url"], r["_excerpt"])
        lines.append("  - id: \"{0}\"".format(r["accession"]))
        lines.append("    prompt: |")
        lines.append(yaml_quote_block(body))
    return "\n".join(lines) + "\n" + SENTINELS


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--allow-thin-t1", action="store_true",
                    help="waive the K-4 minimum-universe guard (owner-reviewed only)")
    ap.add_argument("--max-per-task", type=int, default=0, help="cap items (smoke)")
    args = ap.parse_args()
    man = os.path.join(PKG, "manifest.csv")
    if not os.path.exists(man):
        sys.exit("NEED_INFO: manifest.csv missing — run p1/fetch_edgar_filings.py first")
    t1, t13, missing, seen = [], [], 0, set()
    with open(man) as f:
        for r in csv.DictReader(f):
            key = (r["cik"], r["accession"])
            if key in seen:
                continue
            seen.add(key)
            p = os.path.join(PKG, "{0}_{1}.htm".format(r["cik"], r["accession"]))
            ex = excerpt(p)
            if ex is None:
                missing += 1
                continue
            r["_excerpt"] = ex
            bucket = t13 if any(m in r["query_phrase"].lower() for m in ANT_MARKERS) else t1
            bucket.append(r)
    if args.max_per_task:
        t1, t13 = t1[:args.max_per_task], t13[:args.max_per_task]
    if missing:
        print("WARN: {0} manifest rows have no local .htm (download gaps) — "
              "re-run the harvester to fill".format(missing))
    if not t1 and not t13:
        sys.exit("NEED_INFO: no local filings readable — is this the box?")
    # K-4 guard (audit 2026-07-10): a manifest with implausibly few conversion-
    # family filings must not silently become P1-T1's event universe (the
    # hand-run manifest had 9 vs 401 T13-family). Dozens of managers converted
    # 2021-2026; anything under this floor means harvest phrase coverage or
    # truncation is broken — fix the harvest, don't spec.
    # NOT bypassed by --force: --force means "overwrite existing spec files",
    # and payload i legitimately needs it for that — on 2026-07-10 it also
    # silently waived this guard and armed a 9-filing T1 universe. Bypassing
    # the floor now requires the dedicated flag below.
    MIN_T1 = 40
    if 0 < len(t1) < MIN_T1 and not args.max_per_task and not args.allow_thin_t1:
        print("K-4 GUARD: only {0} conversion-family filings (< {1}) — "
              "refusing to write P1-T1 specs from this manifest. Re-run the "
              "harvester with the expanded phrase family; --allow-thin-t1 "
              "only with an owner-reviewed justification.".format(len(t1), MIN_T1))
        t1 = []
    plans = [
        ("P1-T1-events", "deepseek", T1_RULES, t1,
         "Channel A. kimi benched -> deepseek; B channel is gemini (google) so cross-vendor holds."),
        ("P1-T1-events-B", "qwen", T1_RULES, t1,
         "Channel B (channel_of P1-T1-events), alibaba family (qwen; was google 2026-07-18)."),
        ("P1-T13-ant", "deepseek", T13_RULES, t13,
         "Channel A (ANT/semi-transparent subset)."),
        ("P1-T13-ant-B", "qwen", T13_RULES, t13,
         "Channel B, alibaba family (qwen; was google 2026-07-18)."),
    ]
    for task_id, worker, rules, rows, note in plans:
        if not rows:
            print("{0}: 0 filings in scope — spec not written".format(task_id))
            continue
        dest = os.path.join(L1, task_id + ".yaml")
        if os.path.exists(dest) and not args.force:
            print("{0}: exists, skipping (--force to overwrite)".format(task_id))
            continue
        with io.open(dest, "w", encoding="utf-8") as f:
            f.write(build_spec(task_id, worker, rules, rows, note))
        print("{0}: wrote {1} items -> {2}".format(task_id, len(rows), dest))


if __name__ == "__main__":
    main()
