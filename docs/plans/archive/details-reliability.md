# Opportunity details reliability

## Goal

Ensure a slow or temporarily unavailable upstream procurement service never leaves an opportunity drawer empty.

## Completed work

1. Identified the production `httpx.ReadTimeout` from KIMDIS metadata lookup and made transient failures retry once before returning partial details.
2. Kept the selected opportunity's already-loaded facts visible during enrichment and added a retry action for unavailable live data.
3. Added focused request tests, verified the frontend lint/typecheck/production build, deployed to the VPS, and verified the previously failing reference live.

## Production finding

The VPS logs showed `httpx.ReadTimeout` from the KIMDIS metadata request for
`26REQ019661368`. The exception previously escaped `_khmdhs_json`, so FastAPI
returned a 500 and the frontend hid the drawer content.
