# Garrison’s Barber Studio — standalone Pages source

Only public static site payloads and their reproducible build inputs live here.

Cloudflare Pages: framework **None**; repository root directory `custom/garrisonsbarberstudio`; build command `python3 build.py`; build output directory `_site`.

Use the isolated, explicitly selected production branch for project `garrisonsbarberstudio`. The destination is `https://garrisonsbarberstudio.pages.dev/`, not a shared path. Do not bind this folder to another Pages project.

The build uses Python’s standard library, no network and no package installation. It verifies a pinned manifest, every ZIP checksum, exact allowed file set, file sizes and SHA-256 hashes, rejects links/path traversal/duplicates, and only then publishes `_site`. All archives contain whole files and each is under 8 MiB. `_site` is generated and must not be committed.

No service worker is registered. Canonical, social metadata, web manifest scope/start URL, sitemap and local references use the standalone root.
