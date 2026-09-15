# W021 public-clock decision

## Verdict

The public evidence is sufficient to stop treating UTC and Eastern as equally
plausible **nominal I/B/E/S conventions**. Seasonal ET/DST is the documented
standard convention, and the report/announcement fields are distinct from LSEG
activation fields.

It is not sufficient to certify `ANNTIMS` as the earliest public release or to
assign a record-level accuracy bound. These are separate questions.

## Frozen-support result

Checkpoint 09's hashed primary classifier reports, under
`DISPLAY_AS_AMERICA_NEW_YORK` and the two-analyst eligibility gate:

| Tier | Stocks with >=1 PRE and >=1 POST RTH-60 | Stocks with >=8 PRE and >=4 POST RTH-60 |
|---|---:|---:|
| High | 0 | 0 |
| Low | 0 | 0 |

This is a valid failure of the design defined directly on the database's
nominal report timestamp. It is not proof that a fully repaired earliest-public
calendar would also contain zero eligible stocks. The distinction prevents both
errors: choosing UTC to manufacture support, and treating missing certification
as proof that every event is non-RTH.

## Research state

- `HOLD_DESIGN` for the frozen nominal I/B/E/S RTH/RTH-60 implementation.
- `HOLD_DATA` for the intended earliest-public-time implementation.
- Combined P1 status remains `HOLD_DESIGN + HOLD_DATA`; no identification or
  power claim is supported.

The current Databento quote archive does not resolve this distinction. More
quotes cannot repair announcement-time provenance, and a price response cannot
be used to choose its own event clock.

## Next decision, not silently made here

The PI must choose one amendment path:

1. retain the earliest-public RTH object and acquire/verify an event-time source;
   or
2. redefine the scientific session/estimand around the overwhelmingly
   pre-open/after-close support and rerun the required golden sample and pilot.

Until then, the correct execution action is to stop quote, rank, power and
treatment-effect work.
