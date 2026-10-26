# Don’s Barber Shop — existing Pages project source

This folder is Git-backed build source for the SAME existing `donsbarbershop.pages.dev` Direct Upload project. It does not convert the project to native Git integration and must not create a duplicate project.

Build locally or in an explicitly configured CI job: `python3 build.py` from `custom/donsbarbershop`. Verified public output is `_site`. The project can receive that output by authorized Direct Upload or Wrangler against the existing `donsbarbershop` project. Publishing is a separate operation, not part of this script. Verify the correct account/project/production branch before any deployment.

Cloudflare Direct Upload projects cannot switch to native Git integration. Keep the source in Git if desired, then use Direct Upload CI/explicit upload for this existing project. No GitHub Actions or deployment credentials are configured here.

The offline build verifies a pinned manifest, every ZIP hash, exact allowlisted file set, sizes and SHA-256 hashes, rejects path traversal/links/duplicates, and only then emits `_site`. ZIPs contain whole files and are each under 8 MiB. Do not commit generated `_site`.

All 32 existing published file paths are retained. The owner offer preserves every original price, checkout URL and email; only the explicitly corrected Austin phone is replaced (510-694-9699 / tel:+15106949699). The original 404 is byte-exact. The homepage, truthful hours script and web manifest are intentionally superseded; new custom assets/sections are included. Original pass-through SW remains exact and does not cache content. Headers require revalidation and prevent SW caching. Original robots/noindex and existing top concept banner remain unchanged in this prepared update pending owner/root publication policy.

No private source receipts, contact ledgers, unknown staff portrait, or other project’s source is included in the payload.

## Header and hours correction, 2026-10-26

The reviewed correction retains all 54 previous output paths: 50 files are unchanged, four are updated, and two SVG presentation files embed the original JPEG artwork without redrawing it. The header and leather-to-header transition retain one crest aspect ratio and remove the boxed presentation. The visible weekly schedule, schema and Pacific-time status agree: Monday closed; Tuesday-Friday 9 AM-6 PM; Saturday 8 AM-3 PM; Sunday 10 AM-4 PM. Owner-offer/payment files remain byte-exact. Desktop 1440x900 and mobile 390x844 browser review completed, including repeated forward/reverse scroll and menu navigation.

Run `node test-hours.cjs` after building for Pacific opening/closing boundaries and daylight-saving transitions.
