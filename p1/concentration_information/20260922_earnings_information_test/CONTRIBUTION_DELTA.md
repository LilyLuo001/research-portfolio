# What the earnings pilot adds

This pilot adds a fixed six-issuer, 48-announcement-date, 2023-development/2024-test exercise to the completed ordinary-day and FOMC studies. It asks whether SPY quote and trade history adds predictive content for a company's subsequent midpoint change after conditioning on that company, the sampled other stocks, and ES futures. The two equity feeds measure venue BBOs rather than national SIP NBBO.

The added empirical object is a held-out conditional prediction comparison around candidate earnings clocks, with two grid origins, two venues, matched controls, issuer deletion, date-component deletion and descriptive later paths. It is not a new structural estimator or identification strategy. A correction for unequal event/control availability is part of implementing the original equal-issuer/equal-event objective, not a change of hypothesis.

## Relation to the nearest work

Use the existing [contribution assessment](../20260921_price_discovery_literature/CONTRIBUTION_ASSESSMENT.md) for source versions and reading depth. No new full literature review was performed for this closure.

- Ernst already studies stock-specific information discovery through ETFs and high-weight stocks. Merely finding a positive SPY signal around company earnings does not establish novelty relative to that work.
- Box et al. already examine intraday stock/ETF arbitrage and ordering. Comparing two return-prediction directions does not automatically establish where permanent information is discovered.
- Kosar and Mikhalishchev and Bhojraj et al. already study company-information transmission through ETFs and heterogeneous weighting/inattention. A macro-versus-company-news label alone is not a new contribution.

The bounded value of this exercise is to learn whether the apparent SPY signal survives a richer observable information set, timing-grid sensitivity and issuer dependence, and to document exactly which companies and sessions support it. A failure to reproduce a distinct signal is useful for deciding where to stop investment; it is not proof that ETFs contain no company information or a publishable novelty by itself.

## What this sample cannot establish

The three premarket issuers differ from the three after-hours issuers, while the FOMC study is during regular trading hours and contains a different target population. Differences across these results do not identify a news-type or session treatment effect. Gains from different targets/baselines cannot be added or subtracted as market information shares.

The sample does not measure concentration-driven displacement of research, the breadth of all companies' information incorporated into an ETF, or fundamental pricing accuracy. No EPS, earnings surprise or fundamental-value target is estimated here. Historical sampling weights are not contemporaneous holdings. The shared research question remains meaningful, but a claim that concentration makes active research ineffective is not delivered by this pilot.

The actual decision, its numerical basis and the single next action are in [RESULTS.md](RESULTS.md) and [ADVISER_BRIEF.md](ADVISER_BRIEF.md). They must be read with the corrected-model and independent-review receipts; pre-correction model outputs are historical only.
