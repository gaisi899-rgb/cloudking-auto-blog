#!/usr/bin/env python3
import os, json, re, datetime, pathlib, sys, textwrap, traceback, time
from openai import OpenAI

ROOT = pathlib.Path(__file__).resolve().parents[1]
POSTS_DIR = ROOT / "posts"
INDEX_JSON = POSTS_DIR / "index.json"

MODEL = "gpt-4o-mini"  # günstig & ausreichend
TIMEOUT_S = 30

topics = [
    "Shared Hosting vs. VPS vs. Cloud – welcher Tarif passt für wen?",
    "So richtest du automatisierte Backups für WordPress ein (in 10 Minuten)",
    "CDN erklärt: Bilder und Assets turbo-schnell ausliefern",
    "E-Mail-Hosting: Eigenen Mailserver vs. Anbieter – Vor- & Nachteile",
    "Website umziehen: Zero-Downtime-Migration Schritt für Schritt",
    "Performance-Basics: Caching (Page, Object, Opcode) verstehen",
    "SSL/TLS richtig konfigurieren – HSTS, TLS 1.3 & Co.",
    "Domains clever wählen: SEO, Marke und internationale Endungen",
    "VPN: Nutzen, Grenzen & worauf beim Anbieter zu achten ist",
    "Monitoring & Uptime: Tools und Strategien für kleine Sites",
    "Kostenoptimierung: Von 50€ auf 15€/Monat ohne Leistungseinbruch",
    "E-Mail-Zustellbarkeit: SPF, DKIM, DMARC einfach erklärt",
    "Static vs. Headless CMS: Was ist schneller/billiger zu pflegen?",
    "Failover & Redundanz: Kleine Schritte, große Wirkung",
    "Datenbanken: MySQL vs. PostgreSQL für typische Web-Workloads"
]

def slugify(s: str) -> str:
    s = s.lower()
    for a,b in [("ä","ae"),("ö","oe"),("ü","ue"),("ß","ss")]:
        s = s.replace(a,b)
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

def build_html_page(title, meta, html_body, tags, canonical):
    meta_short = (meta[:152] + "…") if len(meta) > 155 else meta
    head = f"""<!doctype html><html lang='de'><head><meta charset='utf-8'/>
<meta name='viewport' content='width=device-width, initial-scale=1'/>
<title>{title}</title><meta name='description' content='{meta_short}'/>
<link rel='canonical' href='{canonical}'/><link rel='icon' href='../favicon.ico'/>
<link rel='stylesheet' href='../assets/style.css'/></head>
<body><div class='container'>
<nav class='nav'><a class='logo' href='../index.html'><span class='badge'>Cloud</span>King</a>
<div style='display:flex;gap:10px'><a class='btn secondary' href='../blog.html'>Blog</a>
<a class='btn' href='mailto:info@handwerker-whv.de'>Kontakt</a></div></nav>
<article class='card'>"""
    foot = """</article>
<footer><hr/><div style='display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap'>
<div>© <span id='year'></span> CloudKing • Hosting &amp; Cloud Tipps</div>
<div><a href='../impressum.html'>Impressum</a> • <a href='../datenschutz.html'>Datenschutz</a></div>
</div><script>document.getElementById('year').textContent=new Date().getFullYear()</script></footer>
</div></body></html>"""
    return head + html_body + foot

def make_fallback_article(title):
    meta = f"Schneller Leitfaden: {title} – kompakt erklärt mit Praxis-Tipps."
    sections = [
        ("Einführung", "In diesem Beitrag bekommst du einen schnellen, praxisnahen Überblick. Ziel: in wenigen Minuten verstehst du die wichtigsten Entscheidungen und Stolperfallen."),
        ("Worauf es ankommt", "<ul><li>Performance & Zuverlässigkeit</li><li>Kostenkontrolle</li><li>Sicherheit & Backups</li><li>Skalierbarkeit</li></ul>"),
        ("Schritt-für-Schritt", "<ol><li>Status prüfen</li><li>Optionen vergleichen</li><li>Setup umsetzen</li><li>Monitoring aktivieren</li></ol>"),
        ("Häufige Fehler", "<ul><li>Kein Staging/Test</li><li>Backups nie getestet</li><li>SSL/HSTS falsch gesetzt</li><li>DNS-TTL vergessen</li></ul>"),
        ("Fazit", "<ul><li>Klein starten, messbar verbessern</li><li>Automatisieren statt manuell</li><li>Sicherheit regelmäßig testen</li></ul>"),
    ]
    body = [f"<h1>{title}</h1><p class='lead'>{meta}</p>"]
    for h, html in sections:
        body.append(f"<h2>{h}</h2><p>{html}</p>")
    html = "\n".join(body)
    tags = ["Hosting","Cloud","Leitfaden","Basics"]
    return {"title": title, "meta": meta, "tags": tags, "html": html}

def _extract_json_loose(s: str):
    """Versucht JSON aus möglichem Markdown/Noise zu ziehen."""
    if not s:
        return None
    # 1) Code-Fence ```json ... ```
    m = re.search(r"```json\s*(\{.*?\})\s*```", s, re.S|re.I)
    if m:
        try: return json.loads(m.group(1))
        except: pass
    # 2) Erstes '{' bis letztes '}' nehmen
    start = s.find("{")
    end = s.rfind("}")
    if start != -1 and end != -1 and end > start:
        chunk = s[start:end+1]
        try: return json.loads(chunk)
        except: pass
    # 3) Roh versuchen
    try: return json.loads(s)
    except: return None

def generate_article(title):
    # Fallback erzwingen möglich: DISABLE_AI=1
    if os.getenv("DISABLE_AI") == "1":
        return make_fallback_article(title)

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        # Kein Key → Fallback
        return make_fallback_article(title)

    client = OpenAI(api_key=api_key)

    system = "Du bist ein deutscher Tech-Redakteur. Schreibe präzise, nützlich und sachlich."
    user = f"""Gib mir ausschließlich ein JSON-Objekt (ohne Fließtext davor/danach) mit genau diesen Schlüsseln:
{{
  "title": "string",
  "meta": "string (1–2 Sätze Meta-Beschreibung, max. 155 Zeichen nach Möglichkeit)",
  "tags": ["5–8","Tags"],
  "html": "<article>…vollständiger Artikel in HTML, ohne <html> oder <body>…</article>"
}}
Thema/Titelvorschlag: {title}

Schreibe auf Deutsch. Zielgruppe: Einsteiger bis Fortgeschrittene Website-Betreiber.
Struktur: <h1>, Einleitung (<p class='lead'>), sinnvolle <h2>-Abschnitte, Listen, evtl. Tabelle, 1–2 Codebeispiele (<pre><code>…</code></pre>), Abschluss mit Fazit-Bullets.
SEO natürlich, nicht keyword-stuffing. Länge: ~900–1200 Wörter.
Liefere NUR JSON, keine Erklärungen oder Formatierungen drumherum.
"""

    # Bis zu 2 Versuche mit JSON-Response-Format
    for attempt in range(2):
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role":"system","content":system},{"role":"user","content":user}],
            temperature=0.6,
            response_format={"type": "json_object"},
        )
        content = resp.choices[0].message.content or ""
        data = _extract_json_loose(content)
        if data and isinstance(data, dict) and "html" in data:
            return data
        time.sleep(1)

    # Letzter Versuch ohne erzwungenes JSON + robuste Extraktion
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[{"role":"system","content":system},{"role":"user","content":user}],
        temperature=0.6,
    )
    content = resp.choices[0].message.content or ""
    data = _extract_json_loose(content)
    if data and isinstance(data, dict) and "html" in data:
        return data

    # Immer noch nichts → Fallback bauen, Log mitschreiben
    print("WARN: AI lieferte kein valides JSON, Fallback wird genutzt.", file=sys.stderr)
    return make_fallback_article(title)

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
    meta = (data.get("meta", "") or "").strip()
    tags = data.get("tags", [])
    html_body = data.get("html", "")

    canonical = f"posts/{filename}"
    full_html = build_html_page(data.get("title", title), meta, html_body, tags, canonical)
    path.write_text(full_html, encoding="utf-8")

    entry = {
        "title": data.get("title", title),
        "url": f"posts/{filename}",
        "date": today,
        "excerpt": (meta[:152] + "…") if len(meta) > 155 else meta,
        "tags": tags
    }
    idx["posts"] = [p for p in idx.get("posts", []) if p["url"] != entry["url"]]
    idx["posts"].append(entry)
    idx["posts"] = sorted(idx["posts"], key=lambda p: p["date"])[-500:]
    save_index(idx)

    print(f"✅ Generated: {path}")

if __name__ == "__main__":
    main()
