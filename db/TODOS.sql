CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(250) NOT NULL UNIQUE,
    password VARCHAR(250) NOT NULL
);

CREATE TABLE todos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    content VARCHAR(100),
    due DATETIME,
    FOREIGN KEY (user_id) REFERENCES users(id)
    );

CREATE TABLE Spieler (
    spielernr INT AUTO_INCREMENT PRIMARY KEY,
    vorname VARCHAR(20),
    nachname VARCHAR(20),
    tore INT,
    vorlagen INT,
    marktwert INT,
    position VARCHAR(20),
    FOREIGN KEY (team) REFERENCES Club(teamnr)
    );


CREATE TABLE Clubs (
    teamnr INT AUTO_INCREMENT PRIMARY KEY,
    tore INT,
    gegentore INT,
    name VARCHAR(30),
    platzierung INT,
    FOREIGN KEY (liga) REFERENCES Liga(liganr)
    );

CREATE TABLE Cheftrainer (
    trainernr INT AUTO_INCREMENT PRIMARY KEY,
    vorname VARCHAR(20),
    nachname VARCHAR(20),
    FOREIGN KEY (team) REFERENCES Club(teamnr)
    );

CREATE TABLE Liga (
    liganr INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(20),
    land VARCHAR(20)
    );
    
import time
import re
import requests
import pandas as pd

# -------------------------
# Einstellungen
# -------------------------
SEASON_ID = 2025  # Saison 2025/26 bei Transfermarkt
BASE = "https://www.transfermarkt.com"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

REQUEST_DELAY_SEC = 2.0  # ggf. erhöhen, wenn TM blockt

# Liga-Codes bei Transfermarkt:
# Premier League GB1, LaLiga ES1, Serie A IT1, Bundesliga L1, Ligue 1 FR1

CLUBS = [
    # Premier League (Top 5)
    {"club_name": "Arsenal", "tm_id": 11, "wettbewerb_id": "GB1"},
    {"club_name": "Manchester City", "tm_id": 281, "wettbewerb_id": "GB1"},
    {"club_name": "Aston Villa", "tm_id": 405, "wettbewerb_id": "GB1"},
    {"club_name": "Liverpool", "tm_id": 31, "wettbewerb_id": "GB1"},
    {"club_name": "Brentford", "tm_id": 1148, "wettbewerb_id": "GB1"},

    # LaLiga (Top 5)
    {"club_name": "FC Barcelona", "tm_id": 131, "wettbewerb_id": "ES1"},
    {"club_name": "Real Madrid", "tm_id": 418, "wettbewerb_id": "ES1"},
    {"club_name": "Villarreal CF", "tm_id": 1050, "wettbewerb_id": "ES1"},
    {"club_name": "Atlético Madrid", "tm_id": 13, "wettbewerb_id": "ES1"},
    {"club_name": "Espanyol Barcelona", "tm_id": 714, "wettbewerb_id": "ES1"},

    # Serie A (Top 5)
    {"club_name": "Inter", "tm_id": 46, "wettbewerb_id": "IT1"},
    {"club_name": "AC Milan", "tm_id": 5, "wettbewerb_id": "IT1"},
    {"club_name": "SSC Napoli", "tm_id": 6195, "wettbewerb_id": "IT1"},
    {"club_name": "Juventus", "tm_id": 506, "wettbewerb_id": "IT1"},
    {"club_name": "AS Roma", "tm_id": 12, "wettbewerb_id": "IT1"},

    # Bundesliga (Top 5)
    {"club_name": "Bayern München", "tm_id": 27, "wettbewerb_id": "L1"},
    {"club_name": "Borussia Dortmund", "tm_id": 16, "wettbewerb_id": "L1"},
    {"club_name": "Bayer 04 Leverkusen", "tm_id": 15, "wettbewerb_id": "L1"},
    {"club_name": "RB Leipzig", "tm_id": 23826, "wettbewerb_id": "L1"},
    {"club_name": "TSG 1899 Hoffenheim", "tm_id": 533, "wettbewerb_id": "L1"},

    # Ligue 1 (Top 5)
    {"club_name": "RC Lens", "tm_id": 826, "wettbewerb_id": "FR1"},
    {"club_name": "Paris Saint-Germain", "tm_id": 583, "wettbewerb_id": "FR1"},
    {"club_name": "Olympique Marseille", "tm_id": 244, "wettbewerb_id": "FR1"},
    {"club_name": "LOSC Lille", "tm_id": 1082, "wettbewerb_id": "FR1"},
    {"club_name": "Olympique Lyon", "tm_id": 1041, "wettbewerb_id": "FR1"},
]

# -------------------------
# Helpers
# -------------------------

def get_html(url: str) -> str:
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.text

def normalize_market_value(val: str) -> str:
    """
    Normalisiert Transfermarkt-Format z.B. '€80.00m' -> '80 mio'
    oder '€1.20bn' -> '1.2 mrd'
    """
    if not isinstance(val, str):
        return ""
    v = val.strip()
    v = v.replace("€", "").strip()
    v = v.replace(",", "")  # falls mal 1,20
    # m/bn sind auf .com üblich
    v = v.replace("m", " mio")
    v = v.replace("bn", " mrd")
    return v.strip()

def split_name(full: str):
    full = (full or "").strip()
    if not full:
        return "", None
    parts = full.split()
    if len(parts) == 1:
        return parts[0], None
    return parts[0], " ".join(parts[1:])

def sql_escape(s: str) -> str:
    return (s or "").replace("'", "''")

def find_best_table(tables: list[pd.DataFrame], must_have: set[str]) -> pd.DataFrame | None:
    """
    Pickt aus read_html-Tabellen die passendste, indem sie mind. alle Spalten enthält.
    """
    for t in tables:
        cols = set(map(str, t.columns))
        if must_have.issubset(cols):
            return t
    return None

# -------------------------
# Scraper
# -------------------------

def fetch_market_values_by_player(club_tm_id: int) -> dict[str, str]:
    """
    Kader-Seite -> mapping Spielername -> Marktwert
    """
    url = f"{BASE}/-/kader/verein/{club_tm_id}/saison_id/{SEASON_ID}"
    html = get_html(url)
    tables = pd.read_html(html)

    # Auf .com ist die Kader-Tabelle oft die mit Spalten wie 'Player', 'Market value'
    # Wir suchen breit:
    target = None
    for t in tables:
        cols = set(map(str, t.columns))
        if "Player" in cols and ("Market value" in cols or "Market Value" in cols):
            target = t
            break
    if target is None:
        # Fallback: erste Tabelle nehmen, wenn sie 'Player' enthält
        for t in tables:
            if "Player" in set(map(str, t.columns)):
                target = t
                break

    mv = {}
    if target is None:
        return mv

    player_col = "Player"
    mv_col = "Market value" if "Market value" in target.columns else ("Market Value" if "Market Value" in target.columns else None)

    if mv_col is None:
        return mv

    for _, row in target.iterrows():
        name = str(row.get(player_col, "")).strip()
        val = str(row.get(mv_col, "")).strip()
        if name and val and val.lower() != "nan":
            mv[name] = normalize_market_value(val)
    return mv

def fetch_league_stats(club_tm_id: int, wettbewerb_id: str) -> pd.DataFrame:
    """
    Leistungsdaten-Seite -> Tore/Vorlagen NUR für die Liga (wettbewerb_id) & Saison (SEASON_ID)
    """
    url = (
        f"{BASE}/-/leistungsdaten/verein/{club_tm_id}"
        f"/saison_id/{SEASON_ID}/plus/1?wettbewerb_id={wettbewerb_id}"
    )
    html = get_html(url)
    tables = pd.read_html(html)

    # Auf .com enthält die Tabelle typischerweise: Player, Goals, Assists (nicht immer Assists!)
    # Wir suchen nach Player + Goals, Assists optional
    t = find_best_table(tables, must_have={"Player", "Goals"})
    if t is None:
        return pd.DataFrame()

    # Assists ist manchmal nicht vorhanden je nach Ansicht -> dann 0
    if "Assists" not in t.columns:
        t["Assists"] = 0

    # Position kann je nach Tabelle 'Pos.' oder 'Position' heißen
    if "Position" not in t.columns and "Pos." in t.columns:
        t["Position"] = t["Pos."]

    # Nur benötigte Felder
    keep = ["Player", "Position", "Goals", "Assists"]
    for k in keep:
        if k not in t.columns:
            t[k] = ""
    return t[keep].copy()

def build_player_inserts_for_club(club_name: str, club_tm_id: int, wettbewerb_id: str) -> list[str]:
    mv_map = fetch_market_values_by_player(club_tm_id)
    stats = fetch_league_stats(club_tm_id, wettbewerb_id)

    inserts = []
    if stats.empty:
        return inserts

    for _, row in stats.iterrows():
        full_name = str(row.get("Player", "")).strip()
        if not full_name or full_name.lower() == "nan":
            continue

        vor, nach = split_name(full_name)
        pos = str(row.get("Position", "")).strip()
        goals = row.get("Goals", 0)
        assists = row.get("Assists", 0)

        # numeric cleanup
        def to_int(x):
            if pd.isna(x):
                return 0
            s = str(x).strip()
            s = re.sub(r"[^\d]", "", s)
            return int(s) if s.isdigit() else 0

        goals_i = to_int(goals)
        assists_i = to_int(assists)

        market_value = mv_map.get(full_name, "")

        nach_sql = "NULL" if not nach else f"'{sql_escape(nach)}'"

        inserts.append(
            f"('{sql_escape(vor)}', {nach_sql}, '{sql_escape(pos)}', {goals_i}, {assists_i}, "
            f"'{sql_escape(market_value)}', (SELECT id FROM Clubs WHERE name='{sql_escape(club_name)}'))"
        )

    return inserts

def main():
    all_value_rows = []
    for c in CLUBS:
        club_name = c["club_name"]
        tm_id = c["tm_id"]
        wettbewerb_id = c["wettbewerb_id"]

        print(f"Scraping: {club_name} (verein={tm_id}, liga={wettbewerb_id})")
        try:
            rows = build_player_inserts_for_club(club_name, tm_id, wettbewerb_id)
            all_value_rows.extend(rows)
        except Exception as e:
            print(f"  ERROR bei {club_name}: {e}")

        time.sleep(REQUEST_DELAY_SEC)

    if not all_value_rows:
        print("Keine Spieler-Daten gefunden (evtl. Block/HTML-Struktur geändert).")
        return

    sql = (
        "INSERT INTO Spieler (vorname, nachname, position, tore, vorlagen, marktwert, team) VALUES\n"
        + ",\n".join(all_value_rows)
        + ";"
    )
    print(sql)

if __name__ == "__main__":
    main()




