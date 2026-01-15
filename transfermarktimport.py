import os
import re
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

# =====================================================
# HARD DISABLE ALL PROXIES (VERY IMPORTANT)
# =====================================================
for k in [
    "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY",
    "http_proxy", "https_proxy", "all_proxy", "no_proxy"
]:
    os.environ.pop(k, None)

import requests
import pandas as pd
from bs4 import BeautifulSoup

# =========================
# Konfiguration
# =========================
BASE = "https://www.transfermarkt.com"
SEASON_ID = 2025
DELAY_SEC = 8.0  # stark erhöht gegen Block/Rate-Limit

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
    "Connection": "keep-alive",
    "DNT": "1",
    "Upgrade-Insecure-Requests": "1",
}

TOP_LEAGUES = [
    {"liganr": 1, "name": "Premier League", "land": "England", "wettbewerb_id": "GB1"},
    {"liganr": 2, "name": "LaLiga", "land": "Spanien", "wettbewerb_id": "ES1"},
    {"liganr": 3, "name": "Serie A", "land": "Italien", "wettbewerb_id": "IT1"},
    {"liganr": 4, "name": "Bundesliga", "land": "Deutschland", "wettbewerb_id": "L1"},
    {"liganr": 5, "name": "Ligue 1", "land": "Frankreich", "wettbewerb_id": "FR1"},
]

# =========================
# HTTP Session (proxyfrei)
# =========================
SESSION = requests.Session()
SESSION.trust_env = False  # <<< absolut entscheidend

def get_html(url: str) -> str:
    for attempt in range(3):
        try:
            r = SESSION.get(
                url,
                headers=HEADERS,
                timeout=40,
                proxies={"http": None, "https": None},
            )
            if r.status_code == 403:
                raise RuntimeError(f"403 Forbidden (Transfermarkt blockt): {url}")
            r.raise_for_status()
            return r.text
        except Exception as e:
            if attempt == 2:
                raise
            time.sleep(5 + attempt * 5)

def soup(url: str) -> BeautifulSoup:
    return BeautifulSoup(get_html(url), "lxml")

def sleep_polite():
    time.sleep(DELAY_SEC)

def esc(s: Optional[str]) -> str:
    return (s or "").replace("'", "''").strip()

def split_name(full: str) -> Tuple[str, Optional[str]]:
    parts = full.strip().split()
    if len(parts) == 1:
        return parts[0], None
    return parts[0], " ".join(parts[1:])

def mv_to_int_million(s: str) -> int:
    if not s or s == "-":
        return 0
    s = s.lower().replace("€", "").replace(",", "")
    if "bn" in s:
        return int(float(s.replace("bn", "")) * 1000)
    if "m" in s:
        return int(float(s.replace("m", "")))
    if "k" in s:
        return int(float(s.replace("k", "")) / 1000)
    return 0

# =========================
# Club standings
# =========================
@dataclass
class ClubRow:
    teamnr: int
    liganr: int
    name: str
    tm_id: int
    platz: int
    tore: int
    gegentore: int
    wettbewerb_id: str

def fetch_top5_clubs_from_standings(liganr, wettbewerb_id):
    url = f"{BASE}/{wettbewerb_id}/tabelle/wettbewerb/{wettbewerb_id}/saison_id/{SEASON_ID}"
    page = soup(url)
    table = page.select_one("table.items")
    rows = table.select("tbody tr")

    out = []
    for tr in rows:
        rank = tr.select_one("td.zentriert")
        if not rank or not rank.text.isdigit():
            continue
        r = int(rank.text)
        if r > 5:
            continue

        club = tr.select_one("td.hauptlink a")
        href = club.get("href", "")
        tm_id = int(re.search(r"/verein/(\d+)", href).group(1))

        score = re.search(r"(\d+)\s*:\s*(\d+)", tr.text)
        tore, gegentore = (int(score.group(1)), int(score.group(2))) if score else (0, 0)

        out.append((club.text.strip(), tm_id, tore, gegentore, r))

    out.sort(key=lambda x: x[4])
    return [(a, b, c, d) for a, b, c, d, _ in out]

# =========================
# SQL Builder
# =========================
def build_sql() -> str:
    lines = ["SET FOREIGN_KEY_CHECKS=0;"]

    # Liga
    lines.append("INSERT INTO Liga (liganr, name, land) VALUES")
    lines.append(",\n".join(
        f"({l['liganr']}, '{esc(l['name'])}', '{esc(l['land'])}')"
        for l in TOP_LEAGUES
    ) + ";")

    clubs = []
    teamnr = 1
    for l in TOP_LEAGUES:
        for name, tm_id, tore, gegentore in fetch_top5_clubs_from_standings(l["liganr"], l["wettbewerb_id"]):
            clubs.append(ClubRow(teamnr, l["liganr"], name, tm_id, teamnr % 5 + 1, tore, gegentore, l["wettbewerb_id"]))
            teamnr += 1
        sleep_polite()

    lines.append("INSERT INTO Clubs (teamnr, liga, tore, gegentore, name, platzierung) VALUES")
    lines.append(",\n".join(
        f"({c.teamnr},{c.liganr},{c.tore},{c.gegentore},'{esc(c.name)}',{c.platz})"
        for c in clubs
    ) + ";")

    lines.append("SET FOREIGN_KEY_CHECKS=1;")
    return "\n".join(lines)

if __name__ == "__main__":
    print(build_sql())
