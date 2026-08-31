---
title: Buyer history reliability
summary: KIMDIS buyer-history windows retry independently and preserve partial evidence
created: 2026-08-31
author: Codex
tags: [buyer-intelligence, khmdhs, reliability]
---

# Buyer history reliability

KIMDIS buyer history is queried in 180-day windows. A transient failure in one
window must not discard records already retrieved from another.

- Each history request has a 25-second timeout and one bounded retry for timeout, transport, 429, and 5xx failures.
- The lookup continues after an exhausted window failure and returns the successful records.
- Buyer Intelligence reports `partial` when it has incomplete KIMDIS evidence, reserving `error` for a lookup that returned no KIMDIS history at all.
