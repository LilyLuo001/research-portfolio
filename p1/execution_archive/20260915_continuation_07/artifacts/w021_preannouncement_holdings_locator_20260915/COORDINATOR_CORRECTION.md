# Final projection check clarification

The original first-20 checker tested position numbering, not every projected field against raw XML. Its backtrace claim is superseded, not relied upon. The v1 candidate flag also omitted two predicates from the pre-existing convention; v2 restored positive numeric balance and rejection of repeated-character CUSIP sentinels. The observed candidate count remained 39 of 41 positions.

The coordinator added source identity/hash guards, 11 synthetic assertions, and a genuinely independent first-20 fieldwise XML projection comparison. This final check ran on SCC and compared all 14 exported fields for each of 20 positions. It passed without displaying row values. See FIELDWISE_BACKTRACE_RECEIPT.json for source/output/parser/checker hashes. This supersedes the earlier index-only claim in ACQUISITION_RECEIPT.json; historical receipts remain visible.

The validated source is a public September 30, 2022 holdings report for S000032550, predating the directly observed December 15 public conversion notice. Historical US-common-security mapping, denominator and exposure eligibility are downstream checks, not passed by this projection. No raw source was modified, no paid data purchased, and no response or financial-value fields were extracted.
