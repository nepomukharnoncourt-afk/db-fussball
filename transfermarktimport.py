import re
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import requests
import pandas as pd
from bs4 import BeautifulSoup

# =========================
# Konfiguration
# =========================
BASE = "https://www.transfermarkt.com"
SEASON_ID = 2025  # Saison 2025/26 bei Transfermarkt
DELAY_SEC = 2.0   # erhöhen falls Rate-Limit/Block

# Wichtig: "echte" Browser-Header helfen oft gegen 403/Block
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

OUTPUT_SQL = "import_transfermarkt.sql"

TOP_LEAGUES = [
    {"liganr": 1, "name": "Premier League", "land": "England", "wettbewerb_id": "GB1"},
    {"liganr": 2, "name": "LaLiga",        "land": "Spanien",  "wettbewerb_id": "ES1"},
    {"liganr": 3, "name": "Serie A",       "land": "Italien",  "wettbewerb_id": "IT1"},
    {"liganr": 4, "name": "Bundesliga",    "land": "Deutschland", "wettbewerb_id": "L1"},
    {"liganr": 5, "name": "Ligue 1",       "land": "Frankreich",  "wettbewerb_id": "FR1"},
]

# =========================
# HTTP: robust + proxy-frei
# =========================
# Session verwenden, damit Cookies/Keep-Alive genutzt werden
# UND ganz wichtig: trust_env=False -> ignoriert HTTP_PROXY/HTTPS_PROXY Umgebungsvariablen
SESSION = requests.Session()
SESSION.trust_env = False  # <<< DAS ist der Schlüssel gegen ProxyError/403 durch Proxy

def get_html(url: str) -> str:
    """
    Lädt HTML robust:
    - keine Proxies aus der Umgebung
    - Retries mit Backoff
    - klare Fehlermeldung bei 403 (Block/Anti-Bot)
    """
    last_err = None

    # kleine Randomisierung im Backoff (ohne random-import: einfache Staffel)
    backoffs = [0.0, 2.0, 5.0]

    for attempt in range(1, 4):  # 3 Versuche
        try:
            # proxies explizit leer (zusätzlich zu trust_env=False)
            r = SESSION.get(
                url,
                headers=HEADERS,
                timeout=40,
                proxies={"http": None, "https": None},
            )

            # Wenn Transfermarkt blockt, kommt oft 403
            if r.status_code == 403:
                raise RuntimeError(
                    f"403 Forbidden bei {url} (Transfermarkt blockt die Anfrage/Proxy/WAF). "
                    f"Tipp: DELAY_SEC erhöhen, ggf. Headless-Browser nötig."
                )

            r.raise_for_status()
            return r.text

        except Exception as e:
            last_err = e
            # Backoff vor dem nächsten Versuch (wenn noch einer folgt)
            if attempt < 3:
                time.sleep(backoffs[attempt])  # attempt=1 ->2s, attempt=2 ->5s
            else:
                break

    # nach 3 Versuchen:
    raise last_err


def soup(url: str) -> BeautifulSoup:
    return BeautifulSoup(get_html(url), "lxml")

def sleep_polite():
    time.sleep(DELAY_SEC)

def esc(s: Optional[str]) -> str:
    return (s or "").replace("'", "''").strip()

def split_name(full: str) -> Tuple[str, Optional[str]]:
    full = (full or "").strip()
    if not full:
        return "", None
    parts = full.split()
    if len(parts) == 1:
        return parts[0], None
    return parts[0], " ".join(parts[1:])

def mv_to_int_million(mv_raw: str) -> int:
    """
    Transfermarkt .com: €80.00m, €1.20bn, €500k, - etc.
    -> INT in Millionen Euro (gerundet).
    """
    if not mv_raw:
        return 0
    s = mv_raw.strip().lower().replace("€", "").replace(",", "")
    if s in ("-", "nan"):
        return 0

    # Beispiele: "80.00m", "1.20bn", "500k"
    m = re.match(r"^\s*([0-9]*\.?[0-9]+)\s*(bn|m|k)\s*$", s)
    if not m:
        # manchmal steht schon "80.0" ohne suffix -> versuchen
        try:
            return int(round(float(re.sub(r"[^\d.]", "", s))))
        except:
            return 0

    val = float(m.group(1))
    unit = m.group(2)

    if unit == "bn":
        return int(round(val * 1000))  # 1.2bn -> 1200 Mio
    if unit == "m":
        return int(round(val))         # 80m -> 80
    if unit == "k":
        return int(round(val / 1000))  # 500k -> 1 Mio (gerundet)

    return 0

# =========================
# Scrape: Tabelle -> Top 5 Clubs mit tm_id, Platz, Tore, Gegentore
# =========================
@dataclass
class ClubRow:
    teamnr: int         # unsere eigene ID für Clubs
    liganr: int
    name: str
    tm_id: int
    platz: int
    tore: int
    gegentore: int
    wettbewerb_id: str  # Liga-Code für Leistungsdaten

def parse_score(score: str) -> Tuple[int, int]:
    # "50:15" -> (50, 15)
    score = score.strip()
    if ":" not in score:
        return 0, 0
    a, b = score.split(":", 1)
    try:
        return int(a), int(b)
    except:
        return 0, 0

def fetch_top5_clubs_from_standings(liganr: int, wettbewerb_id: str) -> List[Tuple[str, int, int, int]]:
    """
    Gibt Liste aus: (club_name, tm_id, tore, gegentore) für Top 5.
    """
    url = f"{BASE}/{wettbewerb_id}/tabelle/wettbewerb/{wettbewerb_id}/saison_id/{SEASON_ID}"
    page = soup(url)

    table = page.select_one("table.items")
    if not table:
        raise RuntimeError(f"Keine Tabelle gefunden auf {url}")

    out = []
    rows = table.select("tbody tr")
    for tr in rows:
        # Rang:
        rank_el = tr.select_one("td.zentriert")
        if not rank_el:
            continue
        rank_txt = rank_el.get_text(strip=True)
        if not rank_txt.isdigit():
            continue
        rank = int(rank_txt)
        if rank > 5:
            continue

        # Club-Link (enthält /verein/<id>)
        club_a = tr.select_one("td.hauptlink a")
        if not club_a:
            continue
        club_name = club_a.get_text(strip=True)
        href = club_a.get("href", "")
        m = re.search(r"/verein/(\d+)", href)
        if not m:
            continue
        tm_id = int(m.group(1))

        # Tore:Gegentore steht meist in einer Spalte wie "Goals"
        # Wir suchen nach Muster \d+:\d+ in der Zeile:
        tds_text = " | ".join(td.get_text(" ", strip=True) for td in tr.select("td"))
        m2 = re.search(r"(\d+)\s*:\s*(\d+)", tds_text)
        if m2:
            tore, gegentore = int(m2.group(1)), int(m2.group(2))
        else:
            tore, gegentore = 0, 0

        out.append((club_name, tm_id, tore, gegentore, rank))

    # sortieren nach rank, top5
    out.sort(key=lambda x: x[4])
    return [(a, b, c, d) for (a, b, c, d, _) in out]

# =========================
# Scrape: Trainer aus Club-Startseite
# =========================
def fetch_trainer(tm_club_id: int) -> Tuple[str, Optional[str]]:
    """
    Versucht auf der Club-Seite den Coach zu finden.
    """
    url = f"{BASE}/-/startseite/verein/{tm_club_id}/saison_id/{SEASON_ID}"
    page = soup(url)

    # Transfermarkt zeigt Trainer meist im Bereich "Manager" / "Coach"
    # robust: suche nach Label "Manager" / "Coach" und nehme den nächsten Link
    text = page.get_text(" ", strip=True).lower()

    # Versuch 1: direktes Element (häufig: a mit class 'trainer-name' etc. variiert)
    coach_link = page.select_one("a[href*='/profil/trainer/']")
    if coach_link and coach_link.get_text(strip=True):
        full = coach_link.get_text(strip=True)
        return split_name(full)

    # Versuch 2: suche im HTML nach "Manager:" und danach einem Namen-Link
    # fallback: finde alle Links, die nach Trainer-Profil aussehen
    links = page.select("a[href*='/profil/trainer/']")
    if links:
        full = links[0].get_text(strip=True)
        return split_name(full)

    # Kein Treffer
    return ("", None)

# =========================
# Scrape: Marktwerte aus Kader
# =========================
def fetch_market_values(tm_club_id: int) -> Dict[str, int]:
    """
    Kader -> Spielername -> Marktwert (INT Mio)
    """
    url = f"{BASE}/-/kader/verein/{tm_club_id}/saison_id/{SEASON_ID}"
    html = get_html(url)
    tables = pd.read_html(html)

    target = None
    for t in tables:
        cols = set(map(str, t.columns))
        if "Player" in cols and ("Market value" in cols or "Market Value" in cols):
            target = t
            break
    if target is None:
        # fallback: erste Tabelle mit "Player"
        for t in tables:
            if "Player" in set(map(str, t.columns)):
                target = t
                break

    mv = {}
    if target is None:
        return mv

    mv_col = "Market value" if "Market value" in target.columns else ("Market Value" if "Market Value" in target.columns else None)
    if not mv_col:
        return mv

    for _, row in target.iterrows():
        name = str(row.get("Player", "")).strip()
        raw = str(row.get(mv_col, "")).strip()
        if name and raw and raw.lower() != "nan":
            mv[name] = mv_to_int_million(raw)

    return mv

# =========================
# Scrape: Leistungsdaten (nur Liga) -> Tore/Vorlagen/Position
# =========================
def fetch_league_stats(tm_club_id: int, wettbewerb_id: str) -> pd.DataFrame:
    url = (
        f"{BASE}/-/leistungsdaten/verein/{tm_club_id}/"
        f"saison_id/{SEASON_ID}/plus/1?wettbewerb_id={wettbewerb_id}"
    )
    html = get_html(url)
    tables = pd.read_html(html)

    # Erwartete Spalten: Player, Goals, Assists (Assists kann fehlen)
    stats = None
    for t in tables:
        cols = set(map(str, t.columns))
        if "Player" in cols and "Goals" in cols:
            stats = t.copy()
            break

    if stats is None:
        return pd.DataFrame()

    if "Assists" not in stats.columns:
        stats["Assists"] = 0

    # Position-Spalten variieren
    if "Position" not in stats.columns:
        if "Pos." in stats.columns:
            stats["Position"] = stats["Pos."]
        else:
            stats["Position"] = ""

    keep = ["Player", "Position", "Goals", "Assists"]
    for k in keep:
        if k not in stats.columns:
            stats[k] = ""
    return stats[keep].copy()

def to_int(x) -> int:
    if x is None:
        return 0
    s = str(x).strip()
    s = re.sub(r"[^\d]", "", s)
    return int(s) if s.isdigit() else 0

# =========================
# SQL Builder
# =========================
def build_sql() -> str:
    lines: List[str] = []
    lines.append("-- Generated from Transfermarkt")
    lines.append("SET FOREIGN_KEY_CHECKS=0;")
    lines.append("")

    # (Optional) Clean tables (nur wenn du das willst)
    lines.append("-- Optional cleanup")
    lines.append("DELETE FROM Spieler;")
    lines.append("DELETE FROM Cheftrainer;")
    lines.append("DELETE FROM Clubs;")
    lines.append("DELETE FROM Liga;")
    lines.append("")

    # Liga inserts (explizite IDs, damit FK sauber)
    lines.append("INSERT INTO Liga (liganr, name, land) VALUES")
    liga_values = []
    for lg in TOP_LEAGUES:
        liga_values.append(f"({lg['liganr']}, '{esc(lg['name'])}', '{esc(lg['land'])}')")
    lines.append(",\n".join(liga_values) + ";")
    lines.append("")

    # Clubs: aus Tabellen holen
    clubs: List[ClubRow] = []
    next_teamnr = 1

    for lg in TOP_LEAGUES:
        liganr = lg["liganr"]
        wettbewerb_id = lg["wettbewerb_id"]

        top5 = fetch_top5_clubs_from_standings(liganr, wettbewerb_id)
        for (club_name, tm_id, tore, gegentore) in top5:
            clubs.append(
                ClubRow(
                    teamnr=next_teamnr,
                    liganr=liganr,
                    name=club_name,
                    tm_id=tm_id,
                    platz=next_teamnr,  # placeholder; wird unten korrigiert
                    tore=tore,
                    gegentore=gegentore,
                    wettbewerb_id=wettbewerb_id,
                )
            )
            next_teamnr += 1

        sleep_polite()

    # platzierung pro liga korrekt setzen (1..5 je Liga)
    for liganr in set(c.liganr for c in clubs):
        liga_clubs = [c for c in clubs if c.liganr == liganr]
        # Sort nach Tore/Gegentore ist nicht sicher; besser: wir holen rank in fetch_top5.
        # In fetch_top5_clubs_from_standings ist rank schon berücksichtigt,
        # hier bleibt Reihenfolge Top5 -> 1..5:
        for i, c in enumerate(liga_clubs, start=1):
            c.platz = i

    # Clubs insert
    lines.append("INSERT INTO Clubs (teamnr, liga, tore, gegentore, name, platzierung) VALUES")
    club_values = []
    for c in clubs:
        club_values.append(
            f"({c.teamnr}, {c.liganr}, {c.tore}, {c.gegentore}, '{esc(c.name)}', {c.platz})"
        )
    lines.append(",\n".join(club_values) + ";")
    lines.append("")

    # Trainer insert
    lines.append("INSERT INTO Cheftrainer (team, vorname, nachname) VALUES")
    trainer_values = []
    for c in clubs:
        v, n = fetch_trainer(c.tm_id)
        if not v:
            v, n = ("", None)
        nach = "NULL" if not n else f"'{esc(n)}'"
        trainer_values.append(f"({c.teamnr}, '{esc(v)}', {nach})")
        sleep_polite()
    lines.append(",\n".join(trainer_values) + ";")
    lines.append("")

    # Spieler insert
    lines.append("INSERT INTO Spieler (team, vorname, nachname, tore, vorlagen, marktwert, position) VALUES")
    player_values = []
    for c in clubs:
        mv_map = fetch_market_values(c.tm_id)
        sleep_polite()

        stats = fetch_league_stats(c.tm_id, c.wettbewerb_id)
        sleep_polite()

        if stats.empty:
            continue

        for _, row in stats.iterrows():
            full = str(row.get("Player", "")).strip()
            if not full or full.lower() == "nan":
                continue

            vor, nach = split_name(full)
            goals = to_int(row.get("Goals", 0))
            assists = to_int(row.get("Assists", 0))
            pos = str(row.get("Position", "")).strip()

            mv_int = mv_map.get(full, 0)

            nach_sql = "NULL" if not nach else f"'{esc(nach)}'"
            player_values.append(
                f"({c.teamnr}, '{esc(vor)}', {nach_sql}, {goals}, {assists}, {mv_int}, '{esc(pos)}')"
            )

    if not player_values:
        lines.append("-- WARN: keine Spielerwerte erzeugt (evtl. TM blockt / Struktur geändert)")
        lines.append("SELECT 1;")
    else:
        lines.append(",\n".join(player_values) + ";")

    lines.append("")
    lines.append("SET FOREIGN_KEY_CHECKS=1;")
    return "\n".join(lines)

def main():
    sql = build_sql()
    with open(OUTPUT_SQL, "w", encoding="utf-8") as f:
        f.write(sql)
    print(f"OK: {OUTPUT_SQL} geschrieben.")

if __name__ == "__main__":
    main()
