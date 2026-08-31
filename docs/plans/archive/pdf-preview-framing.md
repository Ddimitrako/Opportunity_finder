# PDF preview framing

## Goal

Allow the same-origin document preview modal to render proxied PDFs without weakening framing protection for the rest of the application.

## Completed work

1. Verified that the affected KIMDIS attachment is a valid PDF and that the document proxy returns it successfully.
2. Scoped same-origin framing headers to `/api/documents/pdf` while retaining global frame denial elsewhere.
3. Built and deployed the frontend proxy configuration; nginx syntax validation passed in the VPS container.

## Finding

The global nginx `X-Frame-Options: DENY` header also applied to
`/api/documents/pdf`, causing the browser to reject the proxy response inside
the application's iframe.
