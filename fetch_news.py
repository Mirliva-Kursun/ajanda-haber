"""Ajanda haberleri: RSS akışlarını çekip news.json'a gün gün yazar.

GitHub Actions 3 saatte bir çalıştırır; ajanda (PC ve telefon) dosyayı
raw.githubusercontent.com üzerinden okur. Sadece başlık + link içerir.
"""
import html
import json
import os
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.abspath(__file__))
NEWS = os.path.join(ROOT, "news.json")
TZ = ZoneInfo("Europe/Istanbul")  # gün değişimi Türkiye saatine göre
KEEP_DAYS = 60
PER_CAT = 6
FEEDS = {
    "ai": [("TechCrunch", "https://techcrunch.com/category/artificial-intelligence/feed/"),
           ("The Verge", "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml")],
    "tek": [("The Verge", "https://www.theverge.com/rss/index.xml"),
            ("Wired", "https://www.wired.com/feed/category/business/latest/rss")],
    "girisim": [("Webrazzi", "https://webrazzi.com/feed"),
                ("TechCrunch", "https://techcrunch.com/category/startups/feed/")],
}


def fetch_feed(source, url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Ajanda RSS)"})
    with urllib.request.urlopen(req, timeout=20) as r:
        root = ET.fromstring(r.read(3_000_000))
    out = []
    for el in root.iter():
        if el.tag.rsplit("}", 1)[-1] not in ("item", "entry"):
            continue
        title, link = "", ""
        for c in el:
            ct = c.tag.rsplit("}", 1)[-1]
            if ct == "title":
                title = html.unescape("".join(c.itertext())).strip()
            elif ct == "link" and not link:
                link = (c.get("href") or c.text or "").strip()
        if title and link.startswith(("http://", "https://")):
            out.append({"t": title, "u": link, "s": source})
    return out


def main():
    fresh = {}
    for cat, feeds in FEEDS.items():
        lists = []
        for source, url in feeds:
            try:
                lists.append(fetch_feed(source, url))
            except Exception as e:  # noqa: BLE001  bir akış bozuksa diğerleriyle devam
                print(f"{source} ({cat}): {e}")
        merged, seen = [], set()
        for i in range(max((len(x) for x in lists), default=0)):  # kaynakları sırayla karıştır
            for x in lists:
                if i < len(x) and x[i]["u"] not in seen:
                    seen.add(x[i]["u"])
                    merged.append(x[i])
        if merged:
            fresh[cat] = merged[:PER_CAT]
    if not fresh:
        raise SystemExit("hiç haber gelmedi")
    try:
        with open(NEWS, encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, ValueError):
        data = {}
    now = datetime.now(TZ).date()
    data.setdefault(now.isoformat(), {}).update(fresh)
    cutoff = (now - timedelta(days=KEEP_DAYS)).isoformat()
    data = {k: data[k] for k in sorted(data) if k >= cutoff}
    with open(NEWS, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print(now, {k: len(v) for k, v in fresh.items()})


if __name__ == "__main__":
    main()
