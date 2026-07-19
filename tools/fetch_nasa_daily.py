#!/usr/bin/env python3
"""
Scarica NASA POWER daily (2001-2024) per le citta' in data/nasa_cache/
e salva statistiche derivate in data/nasa_daily/{slug}.json

Uso:
    python3 tools/fetch_nasa_daily.py 3     # test su 3 citta'
    python3 tools/fetch_nasa_daily.py       # tutte (~20-30 min)
Riprende da dove si e' fermato: salta le citta' gia' fatte.
"""
import glob, json, os, sys, time
from collections import defaultdict

import requests

SRC = "data/nasa_cache"
OUT = "data/nasa_daily"
START, END = 2001, 2024
HOT_C = 30.0
URL = "https://power.larc.nasa.gov/api/temporal/daily/point"
FILL = -999.0

os.makedirs(OUT, exist_ok=True)


def slope_per_decade(pairs):
    """Regressione lineare su [(anno, valore)] -> gradi per decennio."""
    pairs = [(x, y) for x, y in pairs if y is not None]
    n = len(pairs)
    if n < 5:
        return None
    sx = sum(x for x, _ in pairs); sy = sum(y for _, y in pairs)
    sxy = sum(x * y for x, y in pairs); sxx = sum(x * x for x, _ in pairs)
    den = n * sxx - sx * sx
    if den == 0:
        return None
    return round((n * sxy - sx * sy) / den * 10, 2)


def pct(sorted_vals, p):
    if not sorted_vals:
        return None
    i = int(round((len(sorted_vals) - 1) * p))
    return round(sorted_vals[i], 1)


def fetch(lat, lon):
    r = requests.get(URL, timeout=180, params={
        "parameters": "T2M,T2M_MAX,T2M_MIN,PRECTOTCORR",
        "community": "AG", "latitude": lat, "longitude": lon,
        "start": f"{START}0101", "end": f"{END}1231", "format": "JSON",
    })
    r.raise_for_status()
    return r.json()["properties"]["parameter"]


def build(slug, lat, lon, p):
    tmax, tmin, tavg, prec = p["T2M_MAX"], p["T2M_MIN"], p["T2M"], p["PRECTOTCORR"]

    by_md = defaultdict(list)          # "07-20" -> [(anno, tmax, tmin)]
    yr_t, yr_sum, yr_win = defaultdict(list), defaultdict(list), defaultdict(list)
    yr_hot = defaultdict(int)
    rec_hot = rec_cold = rec_wet = None

    for k, v in tmax.items():
        if v == FILL:
            continue
        y, m, d = int(k[:4]), k[4:6], k[6:8]
        md = f"{m}-{d}"
        lo = tmin.get(k); lo = None if lo == FILL else lo
        by_md[md].append((y, v, lo))

        av = tavg.get(k)
        if av != FILL:
            yr_t[y].append(av)
            if m in ("06", "07", "08"): yr_sum[y].append(av)
            if m in ("12", "01", "02"): yr_win[y].append(av)
        if v >= HOT_C:
            yr_hot[y] += 1

        date = f"{y}-{m}-{d}"
        if rec_hot is None or v > rec_hot[1]: rec_hot = (date, v)
        if lo is not None and (rec_cold is None or lo < rec_cold[1]): rec_cold = (date, lo)
        pr = prec.get(k)
        if pr not in (None, FILL) and (rec_wet is None or pr > rec_wet[1]): rec_wet = (date, pr)

    norms = {}
    for md, rows in by_md.items():
        highs = sorted(r[1] for r in rows)
        top = max(rows, key=lambda r: r[1])
        lows = [r for r in rows if r[2] is not None]
        bot = min(lows, key=lambda r: r[2]) if lows else None
        norms[md] = {
            "n": len(rows),
            "mean_max": round(sum(highs) / len(highs), 1),
            "p10": pct(highs, 0.10), "p90": pct(highs, 0.90),
            "record_max": round(top[1], 1), "record_max_year": top[0],
            "record_min": round(bot[2], 1) if bot else None,
            "record_min_year": bot[0] if bot else None,
        }

    def avg(d, y): return round(sum(d[y]) / len(d[y]), 2) if d.get(y) else None
    years = sorted(yr_t)
    first = [y for y in years if y <= START + 9]
    last = [y for y in years if y >= END - 9]
    def mean_of(d, ys):
        vals = [avg(d, y) for y in ys if avg(d, y) is not None]
        return round(sum(vals) / len(vals), 2) if vals else None

    ann_s = slope_per_decade([(y, avg(yr_t, y)) for y in years])
    sum_s = slope_per_decade([(y, avg(yr_sum, y)) for y in years])
    span = (years[-1] - years[0]) / 10 if len(years) > 1 else 0

    return {
        "slug": slug, "lat": lat, "lon": lon,
        "period": {"start": years[0], "end": years[-1]},
        "source": "NASA POWER (MERRA-2) daily",
        "daily_norms": norms,
        "warming": {
            "annual_per_decade": ann_s,
            "annual_total": round(ann_s * span, 1) if ann_s else None,
            "summer_per_decade": sum_s,
            "summer_total": round(sum_s * span, 1) if sum_s else None,
        },
        "hot_days": {
            "threshold_c": HOT_C,
            "by_year": {str(y): yr_hot.get(y, 0) for y in years},
            "first_decade_avg": round(sum(yr_hot.get(y, 0) for y in first) / len(first), 1) if first else None,
            "last_decade_avg": round(sum(yr_hot.get(y, 0) for y in last) / len(last), 1) if last else None,
        },
        "records": {
            "hottest": {"date": rec_hot[0], "c": round(rec_hot[1], 1)} if rec_hot else None,
            "coldest": {"date": rec_cold[0], "c": round(rec_cold[1], 1)} if rec_cold else None,
            "wettest": {"date": rec_wet[0], "mm": round(rec_wet[1], 1)} if rec_wet else None,
        },
        "decades": {
            f"{START}-{START+9}": {"annual": mean_of(yr_t, first), "summer": mean_of(yr_sum, first), "winter": mean_of(yr_win, first)},
            f"{END-9}-{END}":     {"annual": mean_of(yr_t, last),  "summer": mean_of(yr_sum, last),  "winter": mean_of(yr_win, last)},
        },
    }


limit = int(sys.argv[1]) if len(sys.argv) > 1 else None
files = sorted(glob.glob(f"{SRC}/*.json"))
todo = []
for f in files:
    slug = os.path.basename(f)[:-5]
    if os.path.exists(f"{OUT}/{slug}.json"):
        continue
    try:
        coords = json.load(open(f))["geometry"]["coordinates"]
        todo.append((slug, coords[1], coords[0]))
    except Exception as e:
        print(f"  skip {slug}: {e}")
if limit:
    todo = todo[:limit]

print(f"Da scaricare: {len(todo)} citta' (gia' fatte: {len(files) - len(todo) if not limit else '?'})\n")
ok = fail = 0
for i, (slug, lat, lon) in enumerate(todo, 1):
    print(f"[{i}/{len(todo)}] {slug} ({lat:.2f},{lon:.2f}) ...", end=" ", flush=True)
    for attempt in range(3):
        try:
            stats = build(slug, lat, lon, fetch(lat, lon))
            json.dump(stats, open(f"{OUT}/{slug}.json", "w"))
            w = stats["warming"]["annual_total"]
            hd = stats["hot_days"]
            print(f"ok  (+{w}C dal 2001, giorni>30C: {hd['first_decade_avg']} -> {hd['last_decade_avg']})")
            ok += 1
            break
        except Exception as e:
            if attempt == 2:
                print(f"FALLITO: {e}")
                fail += 1
            else:
                time.sleep(10)
    time.sleep(2)

print(f"\n>>> ok: {ok}   falliti: {fail}   output: {OUT}/")
