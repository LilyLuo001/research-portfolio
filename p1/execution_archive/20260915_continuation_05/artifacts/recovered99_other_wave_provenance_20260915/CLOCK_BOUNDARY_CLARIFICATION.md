# Existing contract: uncertain announcement clocks

Coordinator check, 2026-09-15. This clarifies the existing rule; it does not amend the specification or construct a new clock.

The proposed contract (SHA256 `00af7d39fd51e9c3c6a9051036f26a68b337f2132848368a729ff8a70d32663f`, `conversion_clock_and_exposure.announcement_clock`) explicitly retains source/timestamp uncertainty and uses the earliest plausible announcement instant for exclusion. It does not require every announcement to have second-level precision.

A supported date or month interval may establish that a particular holdings report or earnings-response window lies strictly before the earliest plausible announcement boundary. That requires the interval to describe the relevant public event, with constituent/package provenance; an internal board date or an unexplained cutoff is not automatically such an interval. A later-known public filing also does not establish that no earlier public announcement existed.

Accordingly, checkpoint 04's zero ready earliest-public timestamps must not become a blanket rejection solely on clock precision. Keep these questions separate:

1. Is the public-event identity and source established?
2. Is its uncertainty interval supported, including the package constituent rule?
3. Is the observation unambiguously outside or inside the relevant regime boundaries?

The present metadata join does not answer those questions or certify any clean/excluded stock-wave. No-match means no match in the pinned exposure-source universe only, not absence from a complete conversion calendar. Candidate and other-wave identity links remain useful evidence without being final eligibility.
