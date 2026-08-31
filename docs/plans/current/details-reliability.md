# Opportunity details reliability

## Goal

Ensure a slow or temporarily unavailable upstream procurement service never leaves an opportunity drawer empty.

## Plan

1. Identify the production failure and make KIMDIS detail requests tolerate timeouts and transient upstream failures.
2. Keep the opportunity summary visible while live enrichment is loading or unavailable, with a clear retry path.
3. Add focused tests, validate the build, and deploy the fix.

## Production finding

The VPS logs show `httpx.ReadTimeout` from the KIMDIS metadata request for
`26REQ019661368`. The exception currently escapes `_khmdhs_json`, so FastAPI
returns a 500 and the frontend hides the drawer content.
