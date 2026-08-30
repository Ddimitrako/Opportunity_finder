---
title: Architecture
summary: FastAPI, React/Vite, SQLite, procurement APIs, and optional OpenAI enrichment
created: 2026-08-30
author: Ddimitrako
tags: [architecture, stack, codebase, conventions]
---

# Architecture

The current implementation of Opportunity Finder. Replacing this stack must not change the product intent in [product.md](product.md).

## Repository layout

- `backend/app/`: FastAPI routes, Pydantic domain models, source adapters, services, and worker.
- `backend/tests/`: pytest unit/integration tests and matchmaking eval fixtures.
- `backend/catalog/`: editable software catalog workbook and snapshot tooling.
- `frontend/src/`: React 19 TypeScript application and Vitest tests.
- `docs/`: project memory, active/archive plans, and focused product research.

## Stack

| Layer | Technology | Notes |
| --- | --- | --- |
| API | FastAPI + Pydantic | Typed JSON APIs and server-side auth middleware |
| UI | React 19 + Vite + TypeScript | Single application with no external component library |
| Persistence | SQLite | Bookmarks, market intelligence, AI cache, settings, and pursuits |
| Sources | ΚΗΜΔΗΣ, TED, Διαύγεια, optional ΓΕΜΗ | HTTP adapters isolate source failures |
| AI | OpenAI Responses API | Optional structured enrichment with deterministic fallbacks |
| Runtime | Docker Compose + nginx | Backend, frontend, and daily market worker |

## Conventions

- Runtime software matching reads generated JSON; the workbook is the editable source of truth.
- New API fields are backward-compatible unless a migration plan says otherwise.
- Secrets stay in ignored env files/VPS configuration and never in Git.
- Tests must avoid live paid AI calls; use fakes/fixtures and explicit integration smoke tests.
- CI runs catalog validation, backend tests, frontend lint, tests, typecheck, and build.

## Pursuit workspace

- `PursuitAssessmentService` applies lifecycle hard gates before weighted Access, Win chance, Delivery fit, and Value/effort factors.
- `app_settings` stores the solo-first company profile and per-workflow AI routes; `pursuits` stores pipeline state and fit feedback in the existing SQLite database.
- `/api/opportunities/search` remains compatible but returns assessment fields and may append qualified private-company signals.
- Private signals enter the Action Feed only from recent official company pages with an evidence URL, confidence/need score of at least 70, and explicit software-language evidence.
- `/api/settings/company-profile`, `/api/settings/ai`, and `/api/pursuits` provide the editable decision envelope, model routing, and lightweight pipeline.
