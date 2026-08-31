# PDF preview framing

## Goal

Allow the same-origin document preview modal to render proxied PDFs without weakening framing protection for the rest of the application.

## Finding

The document proxy returns a valid PDF, but the global nginx `X-Frame-Options: DENY`
header also applies to `/api/documents/pdf`. Browsers therefore reject the PDF inside
the application's iframe.

## Plan

1. Add a narrowly scoped document-proxy location with same-origin framing headers.
2. Build and deploy the frontend proxy configuration.
3. Verify a KIMDIS attachment renders in the live preview modal.
