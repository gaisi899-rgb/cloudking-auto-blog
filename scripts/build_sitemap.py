#!/usr/bin/env python3
import os, json, datetime, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
POSTS = ROOT / "posts"
SITEMAP = ROOT / "sitemap.xml"
def build_url(loc, priority="0.7", changefreq="weekly", lastmod=None):
    if lastmod is None: lastmod = datetime.date.today().isoformat()
    return f"""  <url>
    <loc>{loc}</loc>
    <lastmod>{lastmod}</lastmod>
    <changefreq>{changefreq}</changefreq>
    <priority>{priority}</priority>
  </url>"""
def main():
    base = "https://DEINE-DOMAIN"
    index = json.loads((POSTS / "index.json").read_text(encoding="utf-8"))
    urls = []
    urls.append(build_url(f"{base}/","1.0","weekly"))
    urls.append(build_url(f"{base}/blog.html","0.8","daily"))
    urls.append(build_url(f"{base}/impressum.html","0.3","yearly"))
    urls.append(build_url(f"{base}/datenschutz.html","0.3","yearly"))
    for p in index.get("posts", []):
        urls.append(build_url(f"{base}{p['url']}","0.8","weekly",p.get("date")))
    xml = "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">\n" + "\n".join(urls) + "\n</urlset>\n"
    SITEMAP.write_text(xml, encoding="utf-8")
if __name__ == "__main__":
    main()
