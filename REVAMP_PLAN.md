# Revamp implementation

Authorized: full pipeline fixes, latest available data, UCL ingestion, multi-sport analysis and website redesign.

- [x] Reproducible isolated runtime and lean dependency specification.
- [x] Canonical transactional match storage, provenance, safe upserts and coverage reports.
- [x] Fresh domestic/global football, UCL fixtures/history, basketball and tennis where sources permit.
- [x] One causal feature pipeline, real labels and consistent prediction probabilities.
- [x] Chronological benchmark, model manifests and reproducible training.
- [x] Immutable pre-match prediction journal and correct settlement.
- [x] Redesigned responsive multi-sport website with analysis, results, model evaluation and data coverage.
- [x] Retire unsafe alternate serving paths; compatibility entry points and documentation.
- [x] Regression tests, API and visual verification; final limitations recorded.

Existing source datasets and model files are retained. Replacement data/artifacts use a separate versioned store. Provider failures must be visible, never filled with invented results.

See `audit/REVAMP_DELIVERY.md` for verification and remaining limits.
