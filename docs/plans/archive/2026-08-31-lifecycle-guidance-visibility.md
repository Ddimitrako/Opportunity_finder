# Lifecycle guidance visibility

## Goal

Ensure every loaded opportunity details view has a visible lifecycle guidance header and an explicit fallback when the upstream response does not include guidance.

## Plan

1. [x] Add a safe unknown-stage guidance fallback and render the panel for every loaded detail.
2. [x] Make the collapsed header visibly discoverable and translate its user-facing copy.
3. [x] Validate TypeScript/lint, production build and VPS health; archive this plan.

## Validation notes

- Frontend lint and TypeScript pass locally.
- The VPS production build passes with Node 24; all Compose services are running after deployment.
- The API health endpoint returns `ok`.
