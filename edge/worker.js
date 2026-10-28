// amhsite edge cleaner (Claude, 2026-10-28): strips every "preview concept / not their official site" line from HTML
// on the way out (Austin: no preview text on any site). Static files are untouched; rules = D:/amh-tmp/fix/strip-rules.json.
const RULES = [["<div class=\"(?:preview-banner|pv-banner|pv)\" role=\"note\">(?:(?!</div>)[\\s\\S])*?(?:[Pp]review concept|not their official)(?:(?!</div>)[\\s\\S])*?</div>", ""], ["<div class=\"legal\"><h2>Preview only</h2>(?:(?!</div>)[\\s\\S])*?</div>", ""], ["<h2>This is a preview</h2><p>This website is a preview concept made by AMH \\(Artificial Mind Hive\\) for ([^<]*?)\\. It is not the restaurant(?:’|&#x27;|')s official website and is not run by the restaurant\\.</p>", "<h2>About this website</h2><p>This website was designed by AMH (Artificial Mind Hive) for $1.</p>"], ["<small>Preview concept by</small>", "<small>Website by</small>"], ["<em>Not [^<]{0,120}?official site\\.</em>", ""], ["\\s*[-–—|·]?\\s*\\(?[Pp]review concept\\)?(?: (?:made )?(?:for [^.<\"]{0,120}? )?by AMH)?(?:\\s*[-–—:]\\s*|\\s+)?(?:[Nn]ot (?:their|the) official site\\.?)?", ""], ["\\s*[-–—]?\\s*[Nn]ot (?:their|the) official site\\.?", ""]].map(([a, b]) => [new RegExp(a, 'g'), b]);
export default {
  async fetch(request, env) {
    const res = await env.ASSETS.fetch(request);
    const ct = res.headers.get('content-type') || '';
    if (!ct.includes('text/html')) return res;
    let t = await res.text();
    for (const [rx, rep] of RULES) t = t.replace(rx, rep);
    const h = new Headers(res.headers); h.delete('content-length'); h.delete('etag');
    return new Response(t, { status: res.status, statusText: res.statusText, headers: h });
  }
};
