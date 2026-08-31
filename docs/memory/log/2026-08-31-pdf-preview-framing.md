---
title: PDF preview framing
summary: Same-origin PDF proxy previews are exempt from the application's global frame denial
created: 2026-08-31
author: Codex
tags: [pdf, preview, nginx, security]
---

# PDF preview framing

The document proxy returns a valid PDF for KIMDIS attachments. The blank preview
was caused by the global nginx `X-Frame-Options: DENY` header applying to the
iframe response.

- `/api/documents/pdf` has an explicit nginx location with `X-Frame-Options: SAMEORIGIN` and `Content-Security-Policy: frame-ancestors 'self'`.
- The global frame denial remains in force for every other application response.
