#!/usr/bin/env python3
import os, json, re, random, datetime, pathlib, sys
from openai import OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    print("Missing OPENAI_API_KEY secret", file=sys.stderr); sys.exit(1)
client = OpenAI(api_key=OPENAI_API_KEY)
ROOT = pathlib.Path(__file__).resolve().parents[1]
POSTS_DIR = ROOT / "posts"
INDEX_JSON = POSTS_DIR / "index.json"
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
def slugify(s):
  s=s.lower(); s=re.sub(r"ä","ae",s); s=re.sub(r"ö","oe",s); s=re.sub(r"ü","ue",s); s=re.sub(r"ß","ss",s); s=re.sub(r"[^a-z0-9]+","-",s).strip("-"); return s
def load_index():
  if INDEX_JSON.exists(): return json.loads(INDEX_JSON.read_text(encoding="utf-8"))
  return {"posts":[]}
def save_index(idx):
  INDEX_JSON.write_text(json.dumps(idx, ensure_ascii=False, indent=2), encoding="utf-8")
def pick_title():
  today = datetime.date.today(); return topics[(today.isocalendar().week + today.day) % len(topics)]
def generate_article(title):
  system = "Du bist ein deutscher Tech-Redakteur. Schreibe präzise, nützlich und sachlich."
  user = f\"\"\"Bitte verfasse einen deutschsprachigen Blogartikel als reines HTML (nur <article>…</article>) zum Thema:
Titel: {title}
Regeln:
- Zielgruppe: Einsteiger bis Fortgeschrittene Website-Betreiber.
- Ton: klar, hilfreich, nicht werblich.
- Struktur: <h1>, kurze Einleitung (<p class='lead'>), <h2>-Abschnitte, Listen, ggf. Tabelle, 1–2 Codebeispiele (<pre><code>…), am Ende Fazit-Bullets.
- SEO: natürliche Keywords rund um Hosting/Cloud/Webseite/VPN, nicht übertreiben.
- Länge: 900–1200 Wörter.
- Zusätzlich 1–2-Satz Meta-Beschreibung (plain text) und 5–8 Tags.
Antworte als JSON mit: {{\"title\":\"...\",\"meta\":\"...\",\"tags\":[\"...\"],\"html\":\"<article>…</article>\"}}\"\"\"
  resp = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role":"system","content":system},{"role":"user","content":user}], temperature=0.7)
  content = resp.choices[0].message.content
  m = re.search(r\"\\{.*\\}\\s*$\", content, re.S)
  if not m: raise RuntimeError("Antwort enthielt kein JSON")
  return json.loads(m.group(0))
def build_html_page(title, meta, html_body, tags, canonical):
  meta_short = (meta[:152] + "…") if len(meta)>155 else meta
  head = f\"\"\"<!doctype html><html lang='de'><head><meta charset='utf-8'/>
<meta name='viewport' content='width=device-width, initial-scale=1'/>
<title>{title}</title><meta name='description' content='{meta_short}'/>
<link rel='canonical' href='{canonical}'/><link rel='icon' href='../favicon.ico'/>
<link rel='stylesheet' href='../assets/style.css'/>
<meta property='og:title' content='{title}'/><meta property='og:description' content='{meta_short}'/>
<meta property='og:type' content='article'/><meta property='og:url' content='{canonical}'/>
<meta property='og:image' content='../assets/og-default.svg'/>
<meta name='twitter:card' content='summary_large_image'/><meta name='twitter:title' content='{title}'/>
<meta name='twitter:description' content='{meta_short}'/></head><body><div class='container'>
<nav class='nav'><a class='logo' href='../index.html'><span class='badge'>Cloud</span>King</a>
<div style='display:flex;gap:10px'><a class='btn secondary' href='../blog.html'>Blog</a><a class='btn' href='mailto:info@handwerker-whv.de'>Kontakt</a></div></nav><article class='card'>\"\"\"
  foot = \"\"\"</article><footer><hr/><div style='display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap'><div>© <span id='year'></span> CloudKing • Hosting &amp; Cloud Tipps</div><div><a href='../impressum.html'>Impressum</a> • <a href='../datenschutz.html'>Datenschutz</a></div></div><script>document.getElementById('year').textContent=new Date().getFullYear()</script></footer></div></body></html>\"\"\"
  return head + html_body + foot
def pick_related(all_posts, current_title, current_tags, limit=3):
  cur=set([t.lower() for t in (current_tags or [])]); scored=[]
  for p in all_posts:
    if p.get("title")==current_title: continue
    tags=set([t.lower() for t in (p.get("tags") or [])]); score=len(cur & tags); scored.append((score,p))
  scored.sort(key=lambda x:(x[0], x[1].get("date","")), reverse=True)
  return [p for _,p in scored[:limit]]
def main():
  idx = load_index()
  title = pick_title(); slug = slugify(title)
  today = datetime.date.today().isoformat()
  filename = f"{today}-{slug}.html"; path = POSTS_DIR / filename
  if path.exists():
    filename = f"{today}-{slug}-{datetime.datetime.now().strftime('%H%M')}.html"; path = POSTS_DIR / filename
  data = generate_article(title)
  meta = (data.get("meta","") or "").strip(); tags = data.get("tags",[]); html_body = data.get("html","")
  related = pick_related(idx.get("posts",[]), data.get("title", title), tags)
  if related:
    links = "".join([f"<li><a href='../{p['url']}'>{p['title']}</a></li>" for p in related])
    html_body += f"<hr/><h2>Weiterlesen</h2><ul class='list'>{links}</ul>"
  canonical = f"posts/{filename}"
  full_html = build_html_page(data.get("title", title), meta, html_body, tags, canonical)
  path.write_text(full_html, encoding="utf-8")
  entry = {"title": data.get("title", title), "url": f"posts/{filename}", "date": today, "excerpt": (meta[:152] + "…") if len(meta)>155 else meta, "tags": tags}
  idx["posts"] = [p for p in idx.get("posts",[]) if p["url"] != entry["url"]]; idx["posts"].append(entry)
  idx["posts"] = sorted(idx["posts"], key=lambda p: p["date"])[-500:]; save_index(idx)
  # Rebuild blog list for no-JS
  build_list = "\\n".join([f"<a class='post-item' href='{p['url']}'><div><h3>{p['title']}</h3><p>{p['excerpt']}</p><div class='badge'>{' • '.join((p.get('tags') or [])[:3])}</div></div><time>{p['date']}</time></a>" for p in sorted(idx['posts'], key=lambda p:p['date'], reverse=True)])
  blog_html = (ROOT / "blog.html").read_text(encoding="utf-8")
  new_blog = blog_html.replace("<section id=\"posts\" class=\"grid\" style=\"margin-top:16px\"></section>", f"<section id='posts' class='grid' style='margin-top:16px'>{build_list}</section>")
  (ROOT / "blog.html").write_text(new_blog, encoding="utf-8")
  print(f"Generated: {path}")
if __name__ == "__main__": main()
