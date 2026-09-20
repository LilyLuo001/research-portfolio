# Two-anchor diagnostic rule amendment

Status: retrospective documentation of a **coverage diagnostic**, not approval of a scientific response specification.

The original measurement contract assumes a supported event clock. The two Exxon page-metadata values are not independently certified first-public times, so this run uses each only as an uncertainty interval for testing data plumbing:

- technical baseline target: `lower_bound − 5 minutes`;
- technical post target: `upper_bound + h`, for h = 5, 15, 30, 60 minutes;
- the resulting difference is not an identified return bound and is not used for inference;
- 1-minute endpoints are excluded;
- both dates are development diagnostics; there is no validation set;
- separate status/halt data were not acquired, so carried BBO liveness is unverified;
- statistical independence is not assumed.

The adapter derives PRE/RTH/AFTER from each America/New_York timestamp, rejects unexpected non-BBO records, validates sides/sizes, never future-fills, and never infers halt/withdrawal from stringified flags. The absence of a status feed is an explicit limitation, not silently treated as continuous liveness.

`EQUS.MINI` is outside the original four-venue contract and is governed separately by `COMPOSITE_COVERAGE_DIAGNOSTIC.md`.

