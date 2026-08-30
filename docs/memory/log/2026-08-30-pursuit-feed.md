---
title: Pursuit feed decision
summary: Replace fragmented fit views with a lifecycle-correct Action Feed and explainable pursuit assessment
created: 2026-08-30
author: Ddimitrako
tags: [log, product, architecture, scoring]
---

# 2026-08-30 — Pursuit feed

- Use `Bid now`, `Position early`, and qualified `Outbound` as action types; historical stages feed intelligence only.
- Rank by Access, Win chance, Delivery fit, and Value/effort, with hard gates for named/closed/non-software opportunities.
- Optimize the default ranking for first-win probability using a solo-first company profile.
- Merge software matching, buyer intelligence, and bid analysis into one pursuit dossier.
- Run deterministic/low-cost screening first and deep AI only for the strongest candidates, with caching and bounded cost.
- Admit private-company signals only when they are recent, high-confidence, backed by an official URL, and describe a specific software need; broad corporate news stays in Market Radar.
- Keep Market Radar and legacy bookmarks compatible, but make the Action Feed, pursuit status, and explicit Fit/Not fit feedback the primary workflow.
- Pipeline entry is explicitly manual: tracking creates the pursuit, while Fit/Not fit only records feedback on an existing pursuit and never starts or advances a pipeline automatically.
- Keep opportunity documents and source access in the information drawer instead of duplicating an external source action on each feed card.
