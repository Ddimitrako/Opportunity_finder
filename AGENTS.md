# Opportunity Finder

Decision-first procurement intelligence for a solo-first software company. See [`docs/memory/product.md`](docs/memory/product.md) for the durable product intent and [`docs/memory/architecture.md`](docs/memory/architecture.md) for the current implementation.

<!-- project-memory:start -->
## Project memory

Project memory lives in `docs/memory/`. The index is at [`docs/memory/memory-index.md`](docs/memory/memory-index.md).

**Before suggesting** file layout, naming, dependencies, vendor choices, or conventions: read the index, then read the matching entry. The codebase is the source of truth; verify it before relying on a path or name in memory.

**When a new decision is made**: write or update the relevant memory entry in the same conversation and surface the diff. Memory updates review like code. If the change alters the memory system itself, draft it for explicit approval before writing.

**Entries are concise**: bigger than a commit message, smaller than a design document. Use short rationales. Log filenames use a 1–3 word slug after the date.

**When memory contradicts code**: surface the conflict, trust verified code, then update stale memory.

**Plans** live in `docs/plans/current/`; move completed plans to `docs/plans/archive/`.

<!-- project-memory:end -->

## Working agreement

- Inventory existing code, skills, components, and dependencies before creating replacements.
- Preserve user changes and compatibility unless the active plan explicitly changes them.
- Small/local task: implement directly, validate, then review the diff.
- Non-trivial task: create or update one plan in `docs/plans/current/`, implement, validate, and archive it when complete.
- High-risk task: include migration/failure handling, record the architectural decision, and run stronger tests.
- UI work must follow [`DESIGN.md`](DESIGN.md) and be visually checked at desktop and mobile widths.
- Never expose secrets. OpenAI-backed work must degrade safely when `OPENAI_API_KEY` is unavailable.

## Commands

- Backend tests: `$env:PYTHONPATH='backend'; python -m pytest backend/tests -q`
- Catalog validation: `$env:PYTHONPATH='backend'; python -m app.catalog_import --check`
- Frontend install: `npm --prefix frontend ci`
- Frontend lint: `npm --prefix frontend run lint`
- Frontend tests: `npm --prefix frontend test -- --reporter=dot`
- Frontend build/typecheck: `npm --prefix frontend run build`
- Full local stack: `docker compose up --build`

## Definition of done

The requested behavior is implemented, relevant tests cover success and failure paths, lint/typecheck/build pass, the final diff contains no unrelated edits or secrets, UI changes receive visual validation, and plan/memory documents reflect durable decisions.
