# Six-event historical-clock locator gap

## Result

SCC is reachable with the existing noninteractive login, but no documented
historical publisher CMS/version or release-distribution provenance view was
found in the approved local records. This is a **source-location gap**, not a
connectivity failure and not evidence that such historical records do not
exist.

The requested local aggregate adapter is a validated consumer of a private,
six-row provenance export; it is not a retrieval implementation and contains no
remote path or publisher-source locator. The 2026-09-20 event-clock receipt
likewise records only SEC submissions metadata plus imported prior page metadata.
It explicitly leaves first-public status unresolved. The retained metadata code
defines the six fixed URLs but no historical archive identifier.

## Bounded actions performed

```text
ssh -o BatchMode=yes -o ConnectTimeout=10 qluo@scc1.bu.edu true
# exit 0
```

No SCC directories, file trees, or guessed paths were listed or tested. There
were no documented exact remote receipt/source paths for the required
publisher-history view. No current issuer page was fetched; no page body,
financial field, quote, or licensed row was read.

## Exact materials examined

- `p1/concentration_information/20260921_news_basket_readiness/sources/CUSTODIAN_OPERATION_REQUEST.json`
- `p1/concentration_information/20260921_news_basket_readiness/JOINT_SUPPORT.md`
- `p1/concentration_information/20260921_news_basket_readiness/INDEPENDENT_REVIEW.md`
- `p1/concentration_information/20260920_phase3/event_clock/RECEIPT.json`
- `p1/concentration_information/20260920_phase3/event_clock/CLOCK_SUMMARY.json`
- `p1/concentration_information/20260920_phase3/event_clock/build_event_clock.py`
- `p1/concentration_information/20260921_news_basket_readiness/sources/first_public_adapter.py`

## Concrete requirement to continue

Supply an exact authorized historical record location or six-row export tied to
the fixed URLs: a publisher CMS version-history record or independently
captured release-distribution provenance record. It must provide, where
available, the original release identifier, `initial_publication_at_utc` or
`first_distribution_at_utc`, timezone/offset, version-history identifier, and
an explicit first-public statement. The existing private adapter can then emit
local aggregate counts only. Until that named source is supplied, first-public
status remains `UNKNOWN`; no broader source discovery is authorized.
