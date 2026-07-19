#!/usr/bin/env python3
"""Trova gli URL 404 nelle sitemap di weatherarb.com, breakdown per-sitemap."""
import collections
import concurrent.futures
import xml.etree.ElementTree as ET

import requests

SITEMAPS = [
    "https://weatherarb.com/sitemap-main.xml",
    "https://weatherarb.com/sitemap-index.xml",
    "https://weatherarb.com/sitemap-eu.xml",
    "https://weatherarb.com/sitemap-americas.xml",
    "https://weatherarb.com/sitemap-asia.xml",
    "https://weatherarb.com/sitemap-de.xml",
    "https://weatherarb.com/sitemap-pt.xml",
    "https://weatherarb.com/sitemap-ar.xml",
    "https://weatherarb.com/sitemap-ja.xml",
    "https://weatherarb.com/sitemap-ru.xml",
]

LOC = "{http://www.sitemaps.org/schemas/sitemap/0.9}loc"
HEADERS = {"User-Agent": "WeatherArb-404-checker/1.0"}
MAX_WORKERS = 15

_seen = set()


def fetch_locs(url):
    if url in _seen:
        return []
    _seen.add(url)
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        if r.status_code != 200:
            print(f"  sitemap {url} -> HTTP {r.status_code} (saltata)")
            return []
        root = ET.fromstring(r.content)
    except Exception as e:
        print(f"  errore leggendo {url}: {e}")
        return []
    locs = [el.text.strip() for el in root.iter(LOC) if el.text]
    if root.tag.split("}")[-1] == "sitemapindex":
        out = []
        for child in locs:
            out += fetch_locs(child)
        return out
    return locs


def check(url):
    try:
        r = requests.head(url, headers=HEADERS, timeout=15, allow_redirects=False)
        if r.status_code in (403, 405, 501):
            r = requests.get(url, headers=HEADERS, timeout=15,
                             allow_redirects=False, stream=True)
        return url, r.status_code
    except Exception:
        return url, 0


per_sitemap = {}
all_urls = set()
for sm in SITEMAPS:
    print(f"Leggo {sm} ...")
    _seen.clear()
    locs = fetch_locs(sm)
    per_sitemap[sm] = locs
    all_urls.update(locs)

urls = sorted(all_urls)
print(f"\nURL unici totali: {len(urls):,}  (~5-10 min)\n")

status = {}
with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
    for i, (u, code) in enumerate(ex.map(check, urls), 1):
        status[u] = code
        if i % 1000 == 0:
            print(f"  ...{i:,}/{len(urls):,}")

print("\n================= 404 PER SITEMAP =================")
print(f"{'sitemap':<26} {'tot':>7} {'200':>7} {'3xx':>6} {'404':>6} {'5xx':>5} {'err':>5}")
for sm, locs in per_sitemap.items():
    c = collections.Counter(status.get(u, 0) for u in locs)
    n200 = c.get(200, 0)
    n3xx = sum(v for k, v in c.items() if 300 <= k < 400)
    n404 = c.get(404, 0)
    n5xx = sum(v for k, v in c.items() if 500 <= k < 600)
    nerr = c.get(0, 0)
    name = sm.rsplit("/", 1)[-1]
    print(f"{name:<26} {len(locs):>7,} {n200:>7,} {n3xx:>6,} {n404:>6,} {n5xx:>5,} {nerr:>5,}")

dead = sorted(u for u, code in status.items() if code == 404)
with open("urls_404.txt", "w") as f:
    f.write("\n".join(dead) + ("\n" if dead else ""))
print(f"\n>>> {len(dead):,} URL in 404 -> urls_404.txt")
if dead:
    print("\nEsempi (primi 25):")
    for u in dead[:25]:
        print("   ", u)
