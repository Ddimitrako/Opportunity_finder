---
title: Details reliability
summary: Live source enrichment is best-effort and cannot hide already-loaded opportunity facts
created: 2026-08-31
author: Codex
tags: [details, khmdhs, reliability]
---

# Details reliability

KIMDIS detail lookups can time out after a search row has already been loaded.

- Retry a transient KIMDIS timeout, transport failure, 429, or 5xx once with a short delay.
- Return partial details with the upstream error instead of propagating the exception as a 500.
- The drawer immediately renders the selected search-row facts and source link while live enrichment loads; it remains visible with a retry action if enrichment is unavailable.

This preserves the decision workflow without presenting unavailable source data as verified live detail.
