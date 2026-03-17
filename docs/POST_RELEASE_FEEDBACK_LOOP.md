# Post-Release Feedback Loop Checklist

Use this process after each MVP release to improve ranking quality and reduce noise.

## 1. Review Window

- Review period: first 7 days after release.
- Minimum sample: 30 topic candidates (preferably 50+).

## 2. Collect Signals

- Count topics labeled:
  - `selected_for_post`
  - `published`
  - `not_relevant`
  - `duplicate`
- Capture `Top-15 precision` from manual review.
- Note repeated false positives by source and keyword pattern.

## 3. Diagnose Issues

- If many topics are off-ICP:
  - tighten relevance include/exclude terms.
- If too many duplicates:
  - tighten deduplication and cluster rules.
- If high-scoring but low-value topics appear:
  - rebalance scorer weights (`relevance` up, `volume`/`velocity` down).

## 4. Tuning Actions

- Update:
  - profile terms (niche/ICP/negatives),
  - relevance filter config,
  - scoring weights.
- Document each change with date and rationale in `docs/logs/*session.md`.

## 5. Verify Impact

- Re-run smoke check:
  - `pwsh ./scripts/smoke.ps1 -SkipDockerChecks`
- Compare before/after:
  - precision@15
  - number of excluded noisy topics
  - number of label actions needed per shortlist

## 6. Exit Criteria

- Precision@15 improved or stable with lower curation effort.
- No critical regressions in API/UI flow.
- Team confirms shortlist is usable without manual rework spikes.
