# Buyer history reliability

## Goal

Prevent a transient KIMDIS lookup failure from discarding the buyer-history evidence shown in the opportunity dossier.

## Plan

1. Add bounded retries and an appropriate timeout for KIMDIS buyer-history requests.
2. Preserve successful history windows when another window fails, and expose that state as partial rather than an all-or-nothing error.
3. Add focused tests, validate the frontend, and deploy to the VPS.

## Finding

Buyer history queries span multiple 180-day KIMDIS windows. The existing code performs each request once and aborts the whole history lookup on the first timeout or transient upstream response.
