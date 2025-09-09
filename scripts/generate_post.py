#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CloudKing Post Generator
- erzeugt neue Artikel in /posts
- erstellt automatisch ein Cover-Bild (SVG) in /assets/covers
- aktualisiert posts/index.json
- aktualisiert index.html & blog.html, falls Marker vorhanden sind
"""
import os, json, re, datetime, pathlib, time
from openai import OpenAI

# Pfade
ROOT = pathlib.Path(__file__).resolve().parents[1]
POSTS_DIR = ROOT / "posts"
INDEX_JSON = POSTS_DIR / "index.json"
ASSETS = ROOT / "assets"
COVERS = ASSETS / "covers"

MODEL = "gpt-4o-mini"

# Themen (ASCII-sicher, Umlaute umschrieben)
topics = [
    "Shared Hosting vs. VPS vs. Cloud - welcher Tarif passt fuer wen?",
    "WordPress Backups automatisieren in 10 Minuten",
    "CDN erklaert: Bilder und Assets schnell ausliefern",
    "E-Mail-Hosting: Mailserver vs. Anbieter - Vor- und Nachteile",
    "Website-Umzug: Zero-Downtime-Migration Schritt fuer Schritt",
    "Performance-Basics: Caching verstehen",
    "SSL/TLS konfigurieren - HSTS, TLS 1.3 und mehr",
    "Domains clever waehlen: SEO und Endungen",
    "VPN: Nutzen, Grenzen und worauf achten",
    "Monitoring & Uptime: Tools fuer kleine Sites",
    "Kostenoptimierung: Von 50 EUR auf 15 EUR pro Monat",
    "E-Mail-Zustellbarkeit: SPF, DKIM, DMARC",
    "Static vs. Headless CMS",
    "Failover & Redundanz: Grosse Wirkung",
    "Datenbanken: MySQL vs. PostgreSQL"
]

def slugify(s: str) -> str:
    s = s.lower()
    s = s.replace("ä","ae").replace("ö","oe").replace("ü","ue").replace("ß","ss")
    s = re.sub(r"[^a-z0-9]+","-",s).strip("-")
    return s

def load_index():
    if INDEX_JSON.exists():
        return json.loads(INDEX_JSON.read_text(encoding="utf-8"))
    return {"posts": []}

def save_index(idx):
    INDEX_JSON.write_text(json.dumps(idx, ensure_ascii=False, indent=2), encoding="utf-8")

def pick_title():
    today = datetime.date.today()
    return topics[(today.isocalendar().week + today.day) % len(topics)]

def build_cover_svg(title: str, slug: str) -> str:
    COVERS.mkdir(parents=True, exist_ok=True)
    path = COVERS / f"{slug}.svg"
    svg = f"""<svg xmlns='http://www.w3.org/2000/svg' width='1200' height='630'>
<rect width='100%' height='100%' fill='#0b1220'/>
<text x='60' y='360' font-family='Arial' font-size='54' fill='#e6ebf5' font-weight='700'>{title}</text>
<text x='60' y='430' font-family='Arial' font-size='26' fill='#8be9fd'>CloudKing • Hosting &amp; Cloud</text>
</svg>"""
    path.write_text(svg, encoding="utf-8")
    return f"assets/covers/{slug}.svg"

def build_html_page(title, meta, html_body, tags, canonical, cover_url):
    meta_short = (meta[:152] + "…") if isinstance(meta, str) and len(meta) > 155 else meta
    head = f"""<!doctype html><html lang='de'><head><meta charset='utf-8'/>
<meta name='viewport' content='width=device-width, initial-scale=1'/>
<title>{title}</title><meta name='description' content='{meta_short}'/>
<link rel='canonical' href='{canonical}'/><link rel='stylesheet' href='../assets/style.css'/></head>
<body><div class='container'>
<nav class='nav'><a class='logo' href='../index.html'><span class='badge'>Cloud</span>King</a>
<div><a class='btn secondary' href='../blog.html'>Blog</a><a class='btn' href='mailto:info@handwerker-whv.de'>Kontakt</a></div></nav>
<article class='card'>
<figure><img src='../{cover_url}' alt='{title}' loading='lazy'/></figure>"""
    foot = """</article>
<footer><hr/><div>© <span id='year'></span> CloudKing • Hosting & Cloud Tipps</div>
<script>document.getElementById('year').textContent=new Date().getFullYear()</script></footer>
</div></body></html>"""
    return head + html_body + foot

def make_fallback_article(title):
    meta = f"Schneller Leitfaden: {title}"
    body = f"<h1>{title}</h1><p class='lead'>{meta}</p><h2>Inhalt</h2><p>Dieser Artikel wird automatisch generiert.</p>"
    return {"title": title, "meta": meta, "tags": ["Hosting","Cloud"], "html": body}

def _extract_json_loose(s: str):
    if not s:
        return None
    m = re.search(r"```json\s*(\{.*?\})\s*```", s, re.S|re.I)
    if m:
        try: return json.loads(m.group(1))
        except: pass
    try: return json.loads(s)
    except: return None

def generate_article(title):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return make_fallback_article(title)
    client = OpenAI(api_key=api_key)
    system = "Du bist ein deutscher Tech-Redakteur. Schreibe präzise, nützlich und sachlich."
    user = f"""Gib mir ein JSON-Objekt mit: title, meta, tags[], html (<article>…</article>).
Thema: {title}"""
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[{"role":"system","content":system},{"role":"user","content":user}],
        temperature=0.6,
        response_format={"type": "json_object"},
    )
    data = _extract_json_loose(resp.choices[0].message.content or "")
    if data and isinstance(data, dict) and "html" in data:
        return data
    return make_fallback_article(title)

def _as_str(x):
    if isinstance(x, str): return x
    try: return json.dumps(x, ensure_ascii=False)
    except: return str(x)

def main():
    idx = load_index()
    title = pick_title()
    slug = slugify(title)
    today = datetime.date.today().isoformat()
    filename = f"{today}-{slug}.html"
    path = POSTS_DIR / filename
    if path.exists():
        filename = f"{today}-{slug}-{datetime.datetime.now().strftime('%H%M')}.html"
        path = POSTS_DIR / filename

    data = generate_article(title)

    meta = _as_str(data.get("meta","")).strip()
    tags_raw = data.get("tags", [])
    if not isinstance(tags_raw, (list, tuple)):
        tags_raw = [tags_raw]
    tags = [str(t) for t in tags_raw]

    html_raw = data.get("html","")
    if isinstance(html_raw, str):
        html_body = html_raw
    elif isinstance(html_raw, dict):
        html_body = html_raw.get("html") or _as_str(html_raw)
    else:
        html_body = _as_str(html_raw)

    cover_url = build_cover_svg(data.get("title", title), slug)
    canonical = f"posts/{filename}"
    full_html = build_html_page(data.get("title", title), meta, html_body, tags, canonical, cover_url)
    path.write_text(full_html, encoding="utf-8")

    entry = {
        "title": data.get("title", title),
        "url": f"posts/{filename}",
        "date": today,
        "excerpt": meta,
        "tags": tags,
        "cover": cover_url,
    }
    idx["posts"] = [p for p in idx.get("posts", []) if p["url"] != entry["url"]]
    idx["posts"].append(entry)
    save_index(idx)
    print(f"✅ Generated: {path}")

if __name__ == "__main__":
    main()
