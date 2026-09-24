"""Flatten the local catalog into (freq_mhz, label, lat, lon, dist_mi) rows."""
from paths import RF, FREQ_INDEX, CATALOG, RADIO_DATA, PROGRAMMED, HOME_QTH  # noqa: F401
import json, math, os

HOME = HOME_QTH
CAT = str(CATALOG)
OUT = str(FREQ_INDEX)


def dist(lat, lon):
    if lat is None or lon is None:
        return None
    r = 3958.8
    p1, p2 = math.radians(HOME[0]), math.radians(lat)
    dp = p2 - p1
    dl = math.radians(lon - HOME[1])
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return round(2 * r * math.asin(math.sqrt(a)), 1)


d = json.load(open(CAT, encoding="utf-8"))
rows = []
seen = set()


def add(f, label, lat, lon, kind, tx=None):
    if not f:
        return
    key = (round(f, 5), label)
    if key in seen:
        return
    seen.add(key)
    rows.append(dict(f=round(f, 5), label=label, lat=lat, lon=lon, d=dist(lat, lon), kind=kind, tx=tx))


for fav in d["favorites"]:
    for s in fav["systems"]:
        sl = s.get("label", "")
        for site in s.get("sites", []):
            for tf in site.get("trunk_frequencies", []) if isinstance(site.get("trunk_frequencies"), list) else []:
                ff = tf.get("freq_mhz") if isinstance(tf, dict) else tf
                add(ff, f"{sl} / site {site.get('label')}", site.get("lat"), site.get("lon"), "trunk-site")
        tfs = s.get("trunk_frequencies") or []
        for tf in tfs:
            ff = tf.get("freq_mhz") if isinstance(tf, dict) else tf
            use = tf.get("usage", "") if isinstance(tf, dict) else ""
            add(ff, f"{sl} (trunk {use})", None, None, "trunk")
        for dp in s.get("departments", []):
            for ch in dp.get("channels", []):
                lat = ch.get("lat") if ch.get("lat") is not None else dp.get("lat")
                lon = ch.get("lon") if ch.get("lon") is not None else dp.get("lon")
                add(ch.get("freq_mhz"), f"{fav['favorite_name']} | {dp.get('label')} | {ch.get('label')} [{ch.get('mode')}]",
                    lat, lon, "conv", ch.get("tx_freq_mhz"))

# inspect site structure keys once for trunk frequencies stored differently
sample = next((site for fav in d["favorites"] for s in fav["systems"] for site in s.get("sites", []) if site), None)
print("site keys:", sorted(sample.keys()) if sample else None)
rows.sort(key=lambda r: r["f"])
json.dump(rows, open(OUT, "w"))
print(len(rows), "rows;", sum(1 for r in rows if r["d"] is not None), "with location")
