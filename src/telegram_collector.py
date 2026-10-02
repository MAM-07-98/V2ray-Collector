#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, re, sys, time, html, sqlite3, logging
import requests

DB = os.environ.get("DB_PATH", "collector.db")
CH_FILE = "data/channels.txt"
MAX_PAGES = 5
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"}

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-7s | %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("collector")

PROTOS = "vless|vmess|trojan|ss|ssr|hysteria2?|hy2|tuic|wireguard|wg|socks5?|http"
PATTERN = re.compile(r"(?:" + PROTOS + r")://[^\s\"'<>\\\n\r]+", re.IGNORECASE)

def init_db(p):
    c = sqlite3.connect(p)
    c.execute("CREATE TABLE IF NOT EXISTS configs(id INTEGER PRIMARY KEY AUTOINCREMENT, config TEXT NOT NULL UNIQUE, source TEXT, added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
    # migration: اگر جدول قدیمی بود و ستون‌ها را نداشت، اضافه کن
    cols = [row[1] for row in c.execute("PRAGMA table_info(configs)")]
    if "source" not in cols:
        try:
            c.execute("ALTER TABLE configs ADD COLUMN source TEXT")
        except sqlite3.OperationalError:
            pass
    if "added_at" not in cols:
        try:
            c.execute("ALTER TABLE configs ADD COLUMN added_at TIMESTAMP")
        except sqlite3.OperationalError:
            pass
    c.commit()
    return c

def clean(raw):
    c = html.unescape(raw)
    if "&amp;" in c or "&#" in c:
        c = html.unescape(c)
    c = re.sub(r"[\x00-\x1f\x7f]", "", c.strip().rstrip(".,;،؛"))
    return c.replace("&amp;", "&")

def extract(page):
    decoded = html.unescape(page)
    seen, out = set(), []
    for raw in PATTERN.findall(decoded):
        c = clean(raw)
        if c and len(c) >= 20 and c not in seen:
            seen.add(c)
            out.append(c)
    return out

def fetch(ch, before=None):
    url = f"https://t.me/s/{ch}" + (f"?before={before}" if before else "")
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        return r.text if r.status_code == 200 else None
    except Exception as e:
        log.error(f"fetch error: {e}")
        return None

def oldest_id(page):
    ids = re.findall(r'data-post="[^/]+/(\d+)"', page)
    return min(int(i) for i in ids) if ids else None

def load_channels():
    if not os.path.exists(CH_FILE):
        return ["ConfigsHUB"]
    chs = []
    for line in open(CH_FILE, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        line = line.split()[0].lstrip("@")
        if "t.me/" in line:
            line = line.split("t.me/")[-1].strip("/")
        if line:
            chs.append(line)
    return chs or ["ConfigsHUB"]

def save(conn, cfgs, src):
    n = 0
    for c in cfgs:
        if conn.execute("INSERT OR IGNORE INTO configs(config,source) VALUES(?,?)", (c, src)).rowcount:
            n += 1
    conn.commit()
    return n

def collect(conn, ch):
    log.info(f"═══ @{ch} ═══")
    total, before = 0, None
    for p in range(1, MAX_PAGES + 1):
        page = fetch(ch, before)
        if not page:
            break
        cfgs = extract(page)
        if not cfgs:
            break
        new = save(conn, cfgs, ch)
        total += new
        log.info(f"  page {p}: {len(cfgs)} found, {new} new")
        oid = oldest_id(page)
        if not oid or oid == before:
            break
        before = oid
        time.sleep(1.5)
    return total

def main():
    chs = load_channels()
    log.info(f"Channels: {chs}")
    conn = init_db(DB)
    total = sum(collect(conn, ch) for ch in chs)
    in_db = conn.execute("SELECT COUNT(*) FROM configs").fetchone()[0]
    conn.close()
    log.info(f"New: {total} | Total in DB: {in_db}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
