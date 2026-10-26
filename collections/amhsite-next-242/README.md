# Isolated AMH next242 static collection

242 reviewed business previews, excluding the seven existing QA identities.

Cloudflare project root: `collections/amhsite-next-242`

Build: `python3 build.py --output _site`

Deploy: `npx wrangler deploy --config wrangler.jsonc`

This folder does not change the original Worker exporter, main directory, QA paths, or any other collection. Build performs exact hashes, archive/path/type/size, noindex, media, own-host metadata, and route-set checks before isolated extraction. Do not use unzip or omit the validator.
