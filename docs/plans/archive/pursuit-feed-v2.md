# Pursuit Feed v2

## Goal

Turn Opportunity Finder into a decision-first Action Feed that helps a solo-first company select, investigate, and pursue its first winnable software opportunity.

## Completed workstreams

- [x] Created the `codex/pursuit-feed-v2` implementation branch and established product/agentic memory.
- [x] Normalized ΚΗΜΔΗΣ/TED lifecycle and distinguished bid, positioning, and historical records.
- [x] Added company profile, explainable pursuit assessment, AI routing settings, pipeline, and feedback persistence.
- [x] Replaced the dashboard-first home with a simplified Action Feed and progressive pursuit dossier entry point.
- [x] Added backend/frontend tests, visual validation, migration checks, and documentation.

## Acceptance result

- Named, expired, awarded, contracted, paid, and license/hardware-only records are hard-gated from `Pursue`.
- A ΚΗΜΔΗΣ request without a notice is `Position early`, never `Bid now`; delivery dates are not submission deadlines.
- Every assessed card exposes the four factors, reasons, risks/hard gates, solution route, confidence, and next action.
- Existing bookmarks and Market Radar APIs remain; bookmarks migrate idempotently into the pursuit pipeline.
- Private signals require official recent evidence, explicit software need, and high need/confidence scores.
- Backend tests, catalog validation, frontend lint/tests/build, and desktop/mobile visual checks pass.

## Validation

- Backend: 65 pytest tests.
- Catalog: 100 products and 32 use cases validated.
- Frontend: TypeScript/Vite production build, ESLint, and 11 Vitest tests.
- Browser: desktop and 390×844 mobile layouts inspected with no console errors.

## Rollback

All model fields and SQLite tables are additive. Existing opportunity, bookmark, software match, and market endpoints remain available, so the previous UI behavior can be restored without deleting stored data.
