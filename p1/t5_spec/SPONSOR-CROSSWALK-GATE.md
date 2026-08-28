# OWNER GATE — trust → economic sponsor crosswalk

**Blocks**: §15.3.1 headline inference and §15.3.0's dependence
measurement. **Does NOT block** Gate 0, B1 or B2 — neither uses sponsor
clustering.

## Why this cannot be automated

`family` in `events_merged.csv` is the SEC registrant, not the manager.
Clustering on it splits one decision maker into several and overstates
the number of independent clusters — precision inflated in exactly the
dimension the headline result rests on.

**Name matching generates candidates. It is not evidence** (owner,
2026-08-28). It fails in both directions:

*False negatives* — the same manager under unrelated names:

* `Undiscovered Managers Funds` → JPMorgan — shares no token with
  `JPMorgan Trust I/II/IV`.
* `DFA Investment Dimensions Group Inc.` ↔ `Dimensional Investment
  Group Inc.` — 'DFA' and 'Dimensional' share no token, and this pair
  carries 93.6% of treated mass.

*False positives* — a shared name that is not a shared adviser. Series
trusts host UNRELATED managers: `Advisors Series Trust`, `The RBB
Fund`, `Northern Lights Fund Trust II/IV`, `Two Roads Shared Trust`,
`Trust for Advised Portfolios`, `Manager Directed Portfolios`,
`Investment Managers Series Trust II`, `FundVantage Trust`,
`Professionally Managed Portfolios`. For these the registrant may be a
shell, so the mapping can differ row by row within one registrant and
grouping by trust name would be wrong.

## What you are mapping TO

**The economic entity that plausibly generated the conversion decision**
— the one that would transmit a common organizational shock. Not the
legal trust. **And not automatically the sub-adviser label either.**

Sometimes the decision sits with the sub-adviser. Sometimes it sits with
the trust's own adviser, or with a distribution platform that converted
several sub-advised series at once — in which case those series DO share
a shock and splitting them by sub-adviser would overstate independence.
Reading either label off mechanically is the same error in a different
costume. The question is always: who decided, and whose shock is shared?

### `AMBIGUOUS` is a permitted answer

Where governance genuinely does not resolve, write `AMBIGUOUS` in
`proposed_sponsor` and record in `evidence_locator` what you checked and
why it did not settle. **Do not force the row into a heuristic group.**
A forced row is an unknown that looks settled: the cluster count comes
out confident and wrong, and nothing downstream can tell.

`ambiguous_families()` returns these, and estimation must handle them
explicitly — reporting the headline both with each ambiguous registrant
as its own cluster and merged into its best-guess group. If the
conclusion moves between the two, that is a finding about how much the
crosswalk carries, and it gets stated rather than resolved by picking
the nicer one.

So every row needs a locator: an ADV, a prospectus/SAI adviser section,
an N-CEN, or a registrant series list. Filling any of it from model
knowledge is the hallucination meta-rule 1 forbids.

**Review these four first** — they are where the cluster count actually
moves: **Dimensional** (93.6% of treated mass), **JPMorgan**,
**Fidelity**, and the shared-series-trust rows above.

## Candidate groupings from names — 84 registrants -> 61 name stems

37 registrants fall into 14 multi-registrant candidate groups. **Each
still needs filing evidence before sign-off** — `load_signed()` refuses
a row with no `evidence_locator`, grouped or not:

* **ab** — `AB Bond Fund, Inc.`; `AB Cap Fund, Inc.`; `AB Equity Income Fund`
* **advisors** — `Advisors Series Trust`; `The Advisors' Inner Circle Fund`; `The Advisors' Inner Circle Fund II`
* **blackrock** — `BLACKROCK LARGE CAP SERIES FUNDS, INC.`; `BlackRock ETF Trust`; `BlackRock Funds`; `BlackRock Municipal Bond Fund, Inc.`
* **bny mellon** — `BNY Mellon Funds Trust`; `BNY Mellon Investment Funds IV, Inc.`
* **bridgeway** — `Bridgeway Funds`; `Bridgeway Funds, Inc.`
* **columbia** — `Columbia Funds Series Trust I`; `Columbia Funds Series Trust II`
* **hartford** — `The Hartford Mutual Funds II, Inc.`; `The Hartford Mutual Funds, Inc.`
* **jpmorgan** — `JPMorgan Trust I`; `JPMorgan Trust II`; `JPMorgan Trust IV`
* **managed account series** — `Managed Account Series`; `Managed Account Series II`
* **morgan stanley** — `Morgan Stanley`; `Morgan Stanley ETF Trust`; `Morgan Stanley Institutional Fund Trust`; `Morgan Stanley Pathway Funds`
* **neuberger berman** — `Neuberger Berman Alternative Funds`; `Neuberger Berman Equity Funds`; `Neuberger Berman Income Funds`
* **northern lights** — `NORTHERN LIGHTS FUND TRUST II`; `Northern Lights Fund Trust II`; `Northern Lights Fund Trust IV`
* **sanford c bernstein** — `Sanford C. Bernstein Fund II, Inc.`; `Sanford C. Bernstein Fund, Inc.`
* **thrivent** — `Thrivent Core Funds`; `Thrivent Mutual Funds`

## 3 near-misses — same leading token, NOT merged

These share a first word with another stem. They are very likely the
same manager, but no string fact says so — three unrelated firms
could each begin with the same word — so they are surfaced, not
merged. **Review these first: they are the cheapest real reductions
in the cluster count.**

* `Fidelity Commonwealth Trust II` — no registrant shares this name stem, but these stems share its leading token and MAY be the same manager: fidelity salem street; fidelity summer street
* `Fidelity Salem Street Trust` — no registrant shares this name stem, but these stems share its leading token and MAY be the same manager: fidelity commonwealth; fidelity summer street
* `Fidelity Summer Street Trust` — no registrant shares this name stem, but these stems share its leading token and MAY be the same manager: fidelity commonwealth; fidelity salem street

## The 47 singletons are NOT proven independent

This is the asymmetry that matters. A group found by name is evidence;
a singleton is only *absence* of name evidence. Left unreviewed, each
one counts as another independent cluster — which is the error, not the
safe default.

* `Advisor Managed Portfolios`
* `American Beacon Select Funds`
* `BBH Trust`
* `BG Funds`
* `Baron Select Funds`
* `Calamos Investment Trust`
* `Cohen & Steers Future of Energy Fund, Inc.`
* `DFA Investment Dimensions Group Inc.`
* `Delaware Group Government Fund`
* `Diamond Hill Funds`
* `Dimensional Investment Group Inc.`
* `Fidelity Commonwealth Trust II`
* `Fidelity Salem Street Trust`
* `Fidelity Summer Street Trust`
* `Forum Funds`
* `Franklin Custodian Funds`
* `FundVantage Trust`
* `FundX Investment Trust`
* `Goldman Sachs Trust`
* `Guggenheim Strategy Funds Trust`
* `Guinness Atkinson Funds`
* `Harding, Loevner Funds, Inc.`
* `Investment Managers Series Trust II`
* `Ivy Funds`
* `Legg Mason Trust`
* `Leuthold Funds, Inc.`
* `Manager Directed Portfolios`
* `Matrix Advisors Value Fund, Inc.`
* `Matthews International Funds (dba Matthews Asia Funds)`
* `Metropolitan West Funds`
* `Mirae Asset Discovery Funds`
* `OTG Asset Management (→ ETF Opportunities Trust)`
* `PIMCO Funds`
* `Professionally Managed Portfolios`
* `Putnam Funds Trust`
* `SEI Institutional Managed Trust`
* `Series Portfolios Trust`
* `TCW Metropolitan West Funds`
* `The Lazard Funds, Inc.`
* `The RBB Fund, Inc.`
* `Touchstone Strategic Trust`
* `Trust for Advised Portfolios`
* `Trust for Professional Managers`
* `Two Roads Shared Trust`
* `Undiscovered Managers Funds`
* `VanEck Funds`
* `abrdn Funds`

## What to do

1. Open `sponsor_crosswalk_PROPOSED.csv`.
2. Fill `proposed_sponsor` for **every** row with the entity that
   plausibly made the conversion decision — or `AMBIGUOUS` if the
   governance does not resolve. For a shared series trust the answer
   may be the sub-adviser, the trust's adviser, or a platform; decide
   it, do not read a label.
3. Fill `evidence_locator` on **every** row — including rows the stem
   matcher grouped. A candidate group with no filing behind it is still
   a guess.
4. Initial + date each row in `owner_signoff`.
5. Save as `sponsor_crosswalk_SIGNED.csv`.

`load_signed()` refuses a missing file, an unfilled sponsor, a missing
evidence locator, an unsigned row, or any registrant it omits — so
nothing can run on a partial answer.

