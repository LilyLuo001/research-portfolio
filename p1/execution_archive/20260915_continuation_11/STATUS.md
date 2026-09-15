# P1 continuation 11 — public-standard clock adjudication

Date: 2026-09-15

Overall research state: **HOLD_DESIGN + HOLD_DATA**

The broader public-source search resolves one part of checkpoint 10: seasonal
U.S. Eastern time is the documented standard convention for the relevant
I/B/E/S history timestamps. UTC is no longer an equally supported nominal
interpretation.

This does not turn `ANNTIMS` into a verified earliest-public timestamp. Public
documentation and research usage distinguish announcement/report time from
LSEG activation time, but do not provide a record-level error bound, rounding/
imputation rule, or correction history. Published research also documents
material timestamp errors and sometimes validates I/B/E/S against newswires.

## Decisive consequence

Applying the documented ET/DST convention to the frozen 1,082-key classifier
produces zero analyst-qualified high-tier and zero low-tier stocks with both a
PRE and POST RTH-60 event. Therefore:

- the **database-reported-time frozen RTH/RTH-60 implementation fails its
  necessary support gate** and is `HOLD_DESIGN`;
- the stronger **true earliest-public-time object remains `HOLD_DATA`**, because
  nominal failure is not a proved upper bound on events after timestamp repair;
- quote downloads, rank testing, calibration, power and treatment estimation
  remain stopped.

The earlier 0–60 minute lag scenario is only an illustrative robustness check,
not a validated timestamp-error bound. It also yields zero high/low support but
does not convert the true-time unknown into a proved zero.

## Single next action

Close the existing nominal RTH branch as infeasible. If P1 is to continue,
prepare one explicit PI amendment choosing either (a) acquisition/verification
of earliest-public timestamps from an appropriate events/news source, or (b) a
different pre-open/after-close session estimand with a new golden sample and
pilot. Do not spend further Databento quote credits until that choice is made.

Evidence: [public-standard clock evidence](artifacts/w021_public_clock_adjudication_20260915/PUBLIC_STANDARD_CLOCK_EVIDENCE.md).
