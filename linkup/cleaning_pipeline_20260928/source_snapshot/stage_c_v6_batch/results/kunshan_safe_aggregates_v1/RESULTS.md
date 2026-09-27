# Stage C V6 bounded Kunshan result

The deterministic bottom-hash sample contains 100,000 unique Records-matched USA ads from 2,691,376 eligible unique keys in the fixed 32-shard Kunshan frame. Selection did not use text or parser predictions. The source projection contained 3,922,532 unique description keys, zero duplicate description rows, and 340 Records-unmatched keys. The selected sample had zero empty descriptions and zero company-ID mismatches.

Recovery job `123163300` completed with exit `0:0` in 7 minutes 21 seconds after the initial job had already completed sampling but found a missing remote compact-v2 dependency. Recovery reused the unchanged selected sample and did not rescan or reselect. It produced 100,000 compact ad rows, 494,194 evidence rows, and 47,219 relation candidates with zero parse errors. Three ads hit the evidence cap and are marked incomplete/excluded from semantic denominators. Compact output used 57,010,263 bytes under the 500 MB cap.

The CREATED-queue partition conserves all 100,000 ads: 96,144 are in complete queues from 2015 through 2026Q2, 2,043 are in partial 2026Q3, and 1,813 predate 2015. The primary complete-queue semantic denominator is 96,141 after excluding the three incomplete rows.

Within the 96,144 complete-queue rows, the parser recorded 39,372 education candidate detections, 56,769 education candidate non-detections, and 3 incomplete rows. Experience statuses were 56,332 detected candidates, 38,067 candidate non-detections, 1,742 detected no-experience phrase candidates, and 3 incomplete rows. These are candidate-detection audit counts. They are not true qualification prevalence or validated absence rates; non-detection does not mean the employer had no requirement.

Technology tables separate applicant-context candidates from generic mentions. Technology roles remain unknown/unvalidated, occupation was not joined, and no technology count is interpreted as adoption. All time tables describe delivery snapshot text grouped by the Records CREATED queue, not historical text at CREATED. The frame is a regional 32-shard holding and is not claimed to represent the national or full LinkUp population.
