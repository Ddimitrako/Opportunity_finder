# Buyer history reliability

## Goal

Prevent a transient KIMDIS lookup failure from discarding the buyer-history evidence shown in the opportunity dossier.

## Completed work

1. Added a 25-second timeout and one bounded retry for transient KIMDIS buyer-history failures.
2. Continued across unavailable 180-day windows and returned successful results as a partial history state.
3. Added a focused partial-window test, validated the frontend, deployed to the VPS, and ran the resilience tests in the production image.

## Finding

Buyer history queries span multiple 180-day KIMDIS windows. The prior code performed each request once and aborted the whole history lookup on the first timeout or transient upstream response.
