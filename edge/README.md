# Edge cleaner (Claude, 2026-10-28) — LIVE as amhsite version c1d57dc2

Austin's rule: no "preview concept / not their official site" text on any site. The 1,870 pages in the packs still carry it,
so `worker.js` strips it from HTML on the way out (rules = `strip-rules.json`, also used by `D:/amh-tmp/fix/strip_check.py`).
Static files are served directly; the worker only runs for HTML routes (`run_worker_first` list), to stay inside the free daily cap.

Deploy (same files as live, nothing re-uploaded):
  1. extract every `cloudflare-packs/part-*.zip` into `_site/` (sha256 must match `cloudflare-packs/packs.json`)
  2. `cd edge && npx wrangler@4.127.1 deploy`  (CLOUDFLARE_ACCOUNT_ID = austinsdoors 1d5fae…)
Rollback: previous version e4175931-7b17-479e-a156-8e8c5c3b4816 (`wrangler rollback`).
