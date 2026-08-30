# Opportunity Finder design direction

## Product experience

The interface is a decision workspace, not a generic analytics dashboard. The first viewport must answer: what should I pursue, why, what could block it, and what should I do next.

## Visual direction

- Calm operational UI: warm white surfaces on `#eef2f4`, dark blue-grey text, restrained shadows.
- Primary brand: `#24495a`; information: `#2f7f9f`; positive: `#287a61`; warning: `#b7791f`; destructive: `#9b3434`.
- Use Inter/system sans, tabular numerals for scores and budgets, and sentence case for labels.
- Spacing uses an 8px rhythm. Cards use 12–16px radii; controls are at least 40px high.
- Color never carries meaning alone: pair it with a verdict, icon, or explanatory text.

## Hierarchy and layout

- Decision feed comes before metrics, trends, calendars, source diagnostics, or raw data.
- Each opportunity card shows one verdict, one action type, four compact factors, two reasons, one risk, and one next action.
- Progressive disclosure: card → pursuit dossier → source evidence/raw diagnostics.
- Desktop: compact filter rail or toolbar plus a readable single-column feed; avoid dense grids before results.
- Mobile: one column, sticky primary filters, no horizontal scrolling, actions remain reachable by thumb.

## Component rules

- Reuse existing buttons, badges, drawers, form fields, typography, and spacing before adding variants.
- `Pursue`, `Review`, and `Skip` are the only primary verdicts.
- `Bid now`, `Position early`, and `Outbound` describe action type and must not be styled as verdicts.
- Scores support explanations; they are never the sole call to action.
- Unknown data is shown explicitly and routes to a concrete verification action.
- AI states always show pending/cached/error status and never block deterministic results.

## UX principles

- Correct lifecycle beats apparent relevance: planning, open, award, contract, and payment must never blur together.
- Evidence before confidence: do not present inferred deadlines, incumbents, requirements, or budgets as facts.
- Minimize bid effort: default sorting optimizes first-win probability, delivery fit, and access.
- Keep advanced controls available but secondary; presets cover normal use.
- Empty and failure states must explain what remains usable and what the user can do next.

## Avoid

- Five or more KPI cards above the primary results.
- Multiple unrelated scores for the same opportunity without a clear relationship.
- Long tag clouds, unexplained CPV lists, decorative charts, or raw JSON in the main flow.
- Modals for information that belongs in the dossier, or drawers nested inside drawers.

## Visual validation

For material UI work, run the application and capture/inspect the feed and dossier at approximately 1440px and 390px widths. Verify hierarchy, overflow, keyboard focus, loading/error/empty states, and that the primary action is visible without scanning secondary analytics.
