# Model diagnostic aggregate

This compares frozen V5 applicant-qualification candidates with blind model labels. The labels are model references, not human ground truth, so the counts are diagnostic and are not accuracy estimates.

Primary: `gpt-5.6-terra` on 32 rows. Secondary: `gpt-5.6-sol` on a fixed 8-row subset.

## Primary comparison

| Module | Binary support | TP | FN | FP | TN | Reference explicit absence | V5 predicted explicit absence | Excluded unknown/conflict |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Education | 31 | 19 | 4 | 0 | 8 | 0 | not available | 1 |
| Experience | 30 | 23 | 3 | 1 | 3 | 1 | 1 | 1 |

## Independent subset

- Education: 0 primary/secondary disagreements out of 8; agreed-only V5 comparison support 7 (TP 6, FN 1, FP 0, TN 0).
- Experience: 1 primary/secondary disagreements out of 8; agreed-only V5 comparison support 6 (TP 6, FN 0, FP 0, TN 0).

## Protocol-only label composition

Experience-object and technology-role counts below count evidence objects, including multiple objects per ad. They diagnose labeling protocol use and do not measure V5 accuracy.

```json
{
  "not_v5_accuracy": true,
  "primary32": {
    "experience_object_evidence_counts": {
      "general_work": 7,
      "industry_domain": 10,
      "object_unspecified": 1,
      "occupation_task": 29,
      "specific_tool": 3
    },
    "presence_counts": {
      "education": {
        "explicit_positive": 23,
        "insufficient_text": 1,
        "not_mentioned": 8
      },
      "experience": {
        "explicit_negative": 1,
        "explicit_positive": 26,
        "insufficient_text": 1,
        "not_mentioned": 4
      }
    },
    "rows": 32,
    "technology_role_evidence_counts": {
      "develop_train": 1,
      "implement_integrate": 1,
      "use_operate": 21
    }
  },
  "secondary8": {
    "experience_object_evidence_counts": {
      "general_work": 2,
      "industry_domain": 1,
      "occupation_task": 12,
      "specific_tool": 13
    },
    "presence_counts": {
      "education": {
        "explicit_positive": 7,
        "insufficient_text": 1
      },
      "experience": {
        "explicit_positive": 7,
        "insufficient_text": 1
      }
    },
    "rows": 8,
    "technology_role_evidence_counts": {
      "develop_train": 3,
      "role_unspecified": 1,
      "use_operate": 14
    }
  },
  "unit": "labeled evidence objects (multiple per ad possible)"
}
```

The sample is a calibration diagnostic. With only 32 rows, it supports no full-corpus or per-period inference.
