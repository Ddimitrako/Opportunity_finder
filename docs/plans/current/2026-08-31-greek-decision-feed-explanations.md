# Greek decision-feed explanations

## Goal

Make the decision feed understandable at a glance for a Greek-speaking founder: translate its core labels and add accessible hover/focus explanations for the score, verdicts, KPIs, lifecycle, matching and solution-route chips.

## Plan

1. [x] Inventory the existing card and tooltip patterns, then add one reusable explanation pattern.
2. [x] Translate the decision-feed controls, KPI labels and card labels while preserving backend values and filters.
3. [x] Add concise evidence-aware explanations for source, catalog matching, lifecycle, route, freshness, priority, verdict and confidence.
4. [ ] Run lint, tests and build; visually inspect desktop and mobile; record the durable UI decision and archive this plan.

## Validation notes

- `npm --prefix frontend run lint` passes.
- The local Node 18.17.1 runtime is below the Vite 8 requirement, so local Vitest and the Vite bundling stage cannot start. Verify the production-container build and visual output on the VPS before completing the plan.
