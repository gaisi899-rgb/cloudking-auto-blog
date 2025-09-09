#!/usr/bin/env python3
import os, json, re, datetime, pathlib, sys, time
from openai import OpenAI

# Pfade
ROOT = pathlib.Path(__file__).resolve().parents[1]
POSTS_DIR = ROOT / "posts"
INDEX_JSON = POSTS_DIR / "index.json"
ASSETS = ROOT / "assets"
COVERS = ASSETS / "covers"

# Modell
MODEL = "gpt-4o-mini"

# Themenpool
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
    for a,b in [("ä]()
