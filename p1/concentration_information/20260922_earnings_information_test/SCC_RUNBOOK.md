# SCC data-engineering runbook

All raw I/B/E/S metadata projections, row-level event lists, DBN files,
features and models stay at `/project/econdept/qluo/bidirectional_information_20260922/earnings_information_test_20260922/`.

1. Treat the already-created SCC `manifests/EVENT_MANIFEST.csv`,
   `CONTROL_MANIFEST.csv`, and `REQUEST_MANIFEST.json` as the fixed scope.
   `SCC_REUSE_AUDIT.json` is the receipt-backed audit of that exact request set.
2. Verify release identity and economic date against issuer IR/original
   release/SEC. Do not convert an SEC receipt time, webpage update time,
   conference-call time or availability notice to the first-public clock
   without evidence. The existing I/B/E/S minute remains a labelled candidate
   anchor where the rendered public archive lacks a trustworthy publication
   time; such events cannot support sub-minute ordering claims.
3. Retain the 48-event and 288-request caps. A later primary-source clock repair
   is a sensitivity update, not permission to replace an issuer or event based
   on the response.
4. The executed acquisition used `code/scc_earnings_quote_download.py` and the
   exact fixed candidate-clock manifest for the coarse path/prediction test.
   `code/scc_quote_download_earnings.py` is the engineer's stricter unused
   official-clock guard and is preserved as such. The parallel resume script
   reuses only receipt-complete files and quarantines an interrupted partial.
5. Feed the completed native files into the inherited validated decoder, then
   inherited validated six-block/FOMC decoder. Preserve reset/invalid quote
   states, endpoint validity and exact grid membership.

No command logs environment variables or credentials. Candidate-clock results
must carry their timing limitation. A quote is an estimate, not evidence of a
billing debit.
