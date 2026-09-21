# Actual public source retrieval: six technical probes

18 HTTP attempts produced 13 successful metadata projections. No full page bodies were saved. Direct Business Wire requests failed or timed out; syndicated wire pages retained the upstream release identifiers. Failure to fetch a distributor does not imply no distribution record exists. All requests occurred in 2026, not contemporaneously with the 2023 announcements.

| Event | Newly observed time evidence (Eastern) | What can be concluded |
|---|---|---|
| Exxon 2023-01-31 | Issuer metadata and Nasdaq-syndicated Business Wire agree at 06:30 EST | Corroborated candidate minute anchor, not a proof of earliest global publication |
| Exxon 2023-07-28 | Issuer page says 06:00 EDT; syndicated Business Wire says 06:30 EDT | A 30-minute source conflict must not be resolved by looking at returns |
| UnitedHealth 2023-04-14 | Wire 05:55 EDT; issuer JSON-LD 05:57:23.332 EDT | Wire precedes page metadata by 143.332 seconds; plausible publication sequence, not certified earliest release |
| Apple 2023-02-02 | Wire datePublished 16:30 EST; issuer gives calendar date only | Distribution-minute candidate; modified timestamp is distinct |
| Apple 2023-08-03 | Wire datePublished 16:30 EDT; issuer gives calendar date only | Distribution-minute candidate; modified timestamp is distinct |
| Microsoft 2023-04-25 | PRNewswire 16:07 EDT says the release is already available; issuer advance announcement says after close | Availability notice is an upper observation, not the original release timestamp. Page 03:00 EDT cannot simply be used as the event clock |

The source-time split is three premarket and three after-hours, zero regular-session timestamps. These are distribution/notice classifications, **not** a certified first-public session census or an analysis population. The six probes are four issuers; the broader inventory is eight issuers. Neither automatically represents low-weight companies.

The operational criterion should be a defensible public-release interval with transparent provenance and sensitivity to timing uncertainty, not an impossible proof that no earlier disclosure anywhere could have existed. Currently unresolved source conflict and already-available notices remain distinct from credible candidate wire anchors. An earliest observed source time alone is not a proved lower bound. No scientific certification is awarded by this document.

Sources and exact timestamps are stored in PUBLIC_METADATA_RECEIPT.json and DISTRIBUTOR_RECEIPT.json; CLOCK_SUPPORT.csv retains each source URL. Microsoft’s [advance issuer notice](https://news.microsoft.com/source/2023/04/11/microsoft-announces-quarterly-earnings-release-date-55/) and [PRNewswire notice](https://www.prnewswire.com/news-releases/microsoft-earnings-press-release-available-on-investor-relations-website-301807439.html) were also opened through web retrieval to verify their contextual meaning. The schedule is not evidence of exact actual release time.

Public search snippets and current product pages incidentally displayed financial/market values. They were not extracted as signals, used for sample selection, used in analysis, or saved as empirical inputs. Restricted SCC research responses remain unopened. The projected receipts contain only time/source metadata.
