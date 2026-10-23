# Frontend audit and improvements — 23 October 2026

Scope: active Flask app (`sportslab/`), all six navigation views, football/basketball/tennis state, desktop and mobile usability, and public Railway freshness. The existing green/cream visual identity is retained.

## Implemented

| Finding | Change |
| --- | --- |
| Matchboard silently capped the upcoming list at 40; displayed count was truncated | Validated API pagination, full matching totals, previous/next controls, deterministic ordering. Local UCL exposes 90 upcoming fixtures in pages of 24. |
| Results could not be searched or filtered | Participant search, competition and UTC date filters, reset, and pagination across the completed dataset. |
| Freshness was buried in coverage | Contextual latest-result and serving-model calibration dates, plus an explicit coverage link and old-source count. View refresh explains that it reloads stored data, not providers. |
| Forecast warnings came after probabilities and evidence | Missing-data warnings appear above outcome probabilities. Observed xG remains distinct from model goal forecasts. |
| Underlying evidence was not inspectable | Comparison table for Elo, history size, recent scoring/form, rest, congestion and observed-xG coverage. Last-five scores and dates are visible without hover. |
| Opening a fixture left unrelated form selections | Verified fixture analysis populates competition, participants and date. Search filters and swap controls added to scenario builder. |
| Stale archive participants were indistinguishable | Participant endpoint now reports completed count and latest completed date; the selector displays that history and flags old/missing history. Future fixtures do not count as completed appearances. |
| Journal was a dead end | Reopen the original frozen prediction without recalculation or another save button. Filter by sport and pending/settled/void status. Explain browser-session ownership. |
| Navigation replaced browser history | Page and sport URL state, Back/Forward support, active-page and pressed-state semantics, heading focus and skip link. |
| Slow requests could overwrite a newly selected sport | Request sequence/epoch checks, disabled loading controls, timeout messages and retry panels for main data views. Startup navigation is safe before overview data arrives. |
| Small text and cramped mobile controls | Larger text and 44px controls, wrapped filters, six navigation destinations visible on mobile, responsive comparison tables, reduced-motion support. |
| Match labels could mislead | Cancelled/other statuses shown explicitly, unknown kickoff times labelled, date-only results retain their date; UTC filter/local kickoff distinction documented. |

## Verification

- 23 pytest tests passed, including new pagination/filter/count and completed-history regression tests.
- JavaScript syntax check passed.
- Browser checked at 1440 × 1000 and 390 × 844.
- UCL overview: 90 total upcoming fixtures, 24 on the first page.
- Results search `Arsenal`, competition `CL`: 42 results; next page showed 25–42, without overlap in API regression tests.
- Verified Shakhtar–Sp Lisbon analysis, fixture-to-form population, warning placement and numerical evidence.
- Recorded one local browser-session forecast for functional verification, reopened its frozen payload, and checked Back navigation to the journal. No live Railway journal was changed.
- Tennis search narrowed names; mobile page had no horizontal document overflow.
- No browser JavaScript errors were reported during the tested core flows.

## Live deployment comparison

Read-only checks of https://footypredictor.up.railway.app/ on 23 October returned HTTP 200 for health, overview and models. It still serves September artifacts:

| Item | Railway | Refreshed local snapshot |
| --- | --- | --- |
| UCL latest result | 8 Sep 2026 | 21 Oct 2026 |
| Premier League latest result | 6 Sep 2026 | 19 Oct 2026 |
| NBA latest result | 13 Jun 2026 | 22 Oct 2026 |
| ATP latest result | 29 Aug 2026 | 18 Oct 2026 |
| Football model calibrated through | 8 Sep 2026 | 22 Oct 2026 |

The October public snapshot/model bundle and volume-merge fix are prepared locally from the preceding freshness work. This audit does not constitute a deployed release.

## Remaining priorities

1. **Tennis identity reconciliation (data/model work).** The selector exposed split identities: `Carlos Alcaraz` has 265 archive results through 19 Nov 2024, while `Alcaraz C.` has 114 through 12 Oct 2026. `Jannik Sinner` has 330 archive results through 24 Nov 2024; `Sinner J.` has 111 through 12 Jul 2026. Add reviewed provider-ID mappings, deduplicate overlap, rebuild histories and reevaluate before claiming these identities are unified. The new selection notes make this limitation visible; this pass does not silently merge names or retrain on guessed identities.
2. **Production freshness operations.** Deploy the October bundle, verify the volume merge on Railway, and establish a monitored scheduled ingestion/retraining policy. A frontend refresh button is not a scraper. No schedule was created in this pass.
3. **Account-backed journal and export.** Current records belong to a signed browser session. Durable cross-device access requires an authentication/storage design; no account UI should imply it already exists.
4. **Additional licensed feeds.** Lineups, injuries, current market prices and broad UCL observed xG are absent. They need actual provider integration and source timestamps, not decorative placeholders or inferred values.
5. **Further presentation work.** Opponent names in form rows, richer market-level evaluation, competition-level freshness details and saved search URLs would be useful follow-ons. Existing comparison features and form dates are now visible.
6. **Frontend maintainability and accessibility depth.** The existing script remains framework-free and partly compact. A modular refactor, automated browser regression suite, full contrast audit and screen-reader testing remain useful beyond this functional audit. No claim of complete WCAG certification is made.

Additional correction from the final sport-specific review: tennis result cards display W/L rather than binary 1/0 outcome indicators as if they were set scores. Tennis form and comparison labels likewise avoid claiming set-score coverage.

Screenshots: `frontend-mobile-2026-10-23.jpg` (participant search/history) and `frontend-desktop-2026-10-23.jpg` (overview).
