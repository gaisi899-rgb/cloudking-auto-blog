#!/usr/bin/env python3
import os, json, datetime, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
POSTS = ROOT / "posts"
SITEMAP = ROOT / "sitemap.xml"
BASE = "https://gaisi899-rgb.github.io/cloudking-auto-blog"
def url(loc, priority="0.7", changefreq="weekly", lastmod=None):
    if lastmod is None: lastmod = datetime.date.today().isoformat()
    return f"  <url>\n    <loc>{loc}</loc>\n    <lastmod>{lastmod}</lastmod>\n    <changefreq>{changefreq}</changefreq>\n    <priority>{priority}</priority>\n  </url>"
def main():
    index = json.loads((POSTS / "index.json").read_text(encoding="utf-8"))
    urls = []
    urls.append(url(f"{BASE}/","1.0","weekly"))
    urls.append(url(f"{BASE}/blog.html","0.8","daily"))
    urls.append(url(f"{BASE}/impressum.html","0.3","yearly"))
    urls.append(url(f"{BASE}/datenschutz.html","0.3","yearly"))
    for p in index.get("posts",[]):
        urls.append(url(f"{BASE}/{p['url']}","0.8","weekly",p.get("date")))
    xml = "<?xml version='1.0' encoding='UTF-8'?>\n<urlset xmlns='http://www.sitemaps.org/schemas/sitemap/0.9'>\n" + "\n".join(urls) + "\n</urlset>\n"
    SITEMAP.write_text(xml, encoding="utf-8")
if __name__ == "__main__": main()
