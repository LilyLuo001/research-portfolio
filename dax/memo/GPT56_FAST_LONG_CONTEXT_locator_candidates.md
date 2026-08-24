# Second-locator candidates for GPT56_FAST_LONG_CONTEXT — unverified

**Status:** candidates only. **Nothing here may enter the registry until a
seat that can read these pages verifies them.** Recorded 2026-08-24.

## Why the row is pending

`GPT56_FAST_LONG_CONTEXT`, api_effective_date 2026-08-05, currently cites:

- `source_1` — `https://developers.openai.com/api/docs/changelog`
- `source_2` — `https://developers.openai.com/api/docs/guides/fast-mode`

The machine rule in `validate_event_registry.py` does **not** flag this row:
its F2 weak-second test looks for `/models/`, `deprecations` or `pricing` in
`source_2`, and a guides URL contains none of them. The demotion to
`pending_second_date_locator` was therefore a human judgment, and a correct
one — a guides page establishes that fast mode supports long context, but it
does not independently **date** API availability, which is what the memo's
§1.2 rule requires of a second locator.

## Candidates found, and why they are not yet locators

A web search surfaced the pages below. **CORRECTED 2026-08-24.** An earlier version of this memo attributed the
failure to this session's egress proxy. An SCC seat established that is wrong:
from the same host `www2.census.gov` and `www.onetcenter.org` both return 200,
and `cdn.openai.com` served an 11.8 MB PDF. The block is **origin-side and
specific to openai.com page paths** — both candidate URLs return HTTP 403 with
a bot-management interstitial carrying `<meta http-equiv="refresh">` and no
article body, from two independent networks. **No OpenAI page has been read.** Under meta-rule 1 an
unread page is not an extraction with a locator, and entering one would be the
precise failure the registry exists to prevent — a date that traces to a
summary rather than a source.

| Candidate | Why it might date the release | Caution |
|---|---|---|
| `https://openai.com/api-fast-mode/` | a distinct product page from both current sources, and not a guides/models/deprecations/pricing URL, so it would clear the F2 rule on its face | must actually carry a dated statement of API availability, not just a feature description |
| `https://openai.com/index/gpt-5-6/` | family launch announcement | likely dates the GPT-5.6 family, not the 2026-08-05 fast-mode long-context change specifically — a different event |
| third-party write-ups (DEV, CometAPI, Coursiv, tech-insider) | report an August 5 2026 update | **not first-party.** The registry standard is two independent *dated* locators; a secondary blog restating a vendor claim does not meet it and should not be filed |

## What a verifying seat must check

1. Open `https://openai.com/api-fast-mode/` and find whether it carries a
   dated statement that long-context fast mode became API-available on
   **2026-08-05**. A page that describes the feature without dating it is the
   same weakness the current `source_2` already has.
2. Confirm the URL is distinct from both current sources — the validator
   requires `len(set(sources)) == 2` and both HTTPS.
3. Confirm it contains none of `/models/`, `deprecations`, `pricing`, or the
   F2 rule will reject it.
4. If it dates the release, replace `source_2` and set
   `verification_status = verified`, then run
   `python dax/memo/validate_event_registry.py`.
5. **If it does not date the release, leave the row pending.** A candidate
   event contributes no dose; a wrongly-verified one contaminates the dose
   path for every occupation. Pending is the safe state and costs nothing.

## Verification attempted 2026-08-24 — still pending

`https://openai.com/api-fast-mode/` was requested from two independent
networks: this workstation (HTTP 403, 9,701 bytes) and `scc1.bu.edu`
(HTTP 403, 9,913 bytes). `https://openai.com/index/gpt-5-6/` behaves the same.
Every response is a bot-management interstitial — HTML carrying
`<meta http-equiv="refresh" content="360">` and no article body.

This is **not** the egress failure the previous session recorded. From the
same SCC host, `www2.census.gov` and `www.onetcenter.org` both return 200, and
`cdn.openai.com` served an 11.8 MB PDF in the preceding task. The block is
origin-side and specific to `openai.com` page paths.

No attempt was made to defeat the challenge. A page obtained by circumventing
an access control is not a citable locator.

So the page has still not been read, and under meta-rule 1 an unread page
cannot date anything. **`verification_status` remains
`pending_second_date_locator`; the row was not edited.**
`validate_event_registry.py` passes with the row unchanged: 21 rows,
eligible=4, candidate=16, excluded=1, pending_second_date_locator=1.

The third-party write-ups were not filed, and should not be.

What would actually settle this: a seat on a network that renders the page, or
the owner opening it in a browser and pasting the dated line.

## Scale

This is one candidate row of 21. It is not eligible, so it currently
contributes nothing to the dose path, and clearing it adds one event rather
than unblocking a stage.


## Attempt log — 2026-08-24

An SCC seat attempted verification and correctly stopped. `openai.com/api-fast-mode/`
returned 403 with a bot-management interstitial from both a workstation (9,701
bytes) and the SCC (9,913 bytes); `openai.com/index/gpt-5-6/` behaved
identically. No attempt was made to defeat the challenge, on the grounds that a
page obtained by circumventing an access control is not a citable locator —
which is right, and is recorded so the next seat does not repeat the attempt.

`verification_status` remains `pending_second_date_locator`. The registry
validator passes: 21 rows; eligible=4, candidate=16, excluded=1, pending=1.

**What would settle it:** a seat on a network that renders the page, or the
owner opening it in a browser and pasting the dated line. Neither is urgent —
the row is a candidate contributing no dose.
