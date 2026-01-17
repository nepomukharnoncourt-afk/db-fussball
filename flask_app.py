from flask import Flask, redirect, render_template, request, url_for, session, flash
from dotenv import load_dotenv
import os
import git
import hmac
import hashlib
from db import db_read, db_write, get_conn
from auth import login_manager, authenticate, register_user
from flask_login import login_user, logout_user, login_required, current_user
import logging



logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

# Load .env variables
load_dotenv()
W_SECRET = os.getenv("W_SECRET")

# Init flask app
app = Flask(__name__)
app.config["DEBUG"] = True
app.secret_key = "supersecret"


# Admin
ADMIN_PASSWORD = "goatedinfoprojekt"



# Init auth
login_manager.init_app(app)
login_manager.login_view = "login"

# DON'T CHANGE
def is_valid_signature(x_hub_signature, data, private_key):
    hash_algorithm, github_signature = x_hub_signature.split('=', 1)
    algorithm = hashlib.__dict__.get(hash_algorithm)
    encoded_key = bytes(private_key, 'latin-1')
    mac = hmac.new(encoded_key, msg=data, digestmod=algorithm)
    return hmac.compare_digest(mac.hexdigest(), github_signature)

# DON'T CHANGE
@app.post('/update_server')
def webhook():
    x_hub_signature = request.headers.get('X-Hub-Signature')
    if is_valid_signature(x_hub_signature, request.data, W_SECRET):
        repo = git.Repo('./mysite')
        origin = repo.remotes.origin
        origin.pull()
        return 'Updated PythonAnywhere successfully', 200
    return 'Unathorized', 401

# Auth routes
@app.route("/login", methods=["GET", "POST"])
def login():
    error = None

    if request.method == "POST":
        user = authenticate(
            request.form["username"],
            request.form["password"]
        )

        if user:
            login_user(user)

            # NEW: respect ?next=... so redirects from @login_required work correctly
            next_url = request.args.get("next")
            if next_url:
                return redirect(next_url)

            return redirect(url_for("index"))

        error = "Benutzername oder Passwort ist falsch."

    return render_template(
        "auth.html",
        title="In dein Konto einloggen",
        action=url_for("login"),
        button_label="Einloggen",
        error=error,
        footer_text="Noch kein Konto?",
        footer_link_url=url_for("register"),
        footer_link_label="Registrieren"
    )


@app.route("/register", methods=["GET", "POST"])
def register():
    error = None

    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        ok = register_user(username, password)
        if ok:
            return redirect(url_for("login"))

        error = "Benutzername existiert bereits."

    return render_template(
        "auth.html",
        title="Neues Konto erstellen",
        action=url_for("register"),
        button_label="Registrieren",
        error=error,
        footer_text="Du hast bereits ein Konto?",
        footer_link_url=url_for("login"),
        footer_link_label="Einloggen"
    )

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))


# App routes
@app.route("/", methods=["GET"])
@login_required
def index():
    return render_template("main_page.html")

@app.post("/complete")
@login_required
def complete():
    todo_id = request.form.get("id")
    db_write("DELETE FROM todos WHERE user_id=%s AND id=%s", (current_user.id, todo_id,))
    return redirect(url_for("index"))



@app.route("/users", methods=["GET"])
@login_required
def users():
    users = db_read("SELECT username FROM users ORDER BY username", ())
    return render_template("users.html", users=users)


#Chatgpt

@app.route("/dbexplorer", methods=["GET", "POST"])
@login_required
def dbexplorer():
    q = ""
    club_players = []
    player_rows = []
    coach_rows = []
    league_teams = []

    if request.method == "POST":
        q = (request.form.get("q") or "").strip()

        if q:
            like = f"%{q}%"

            # 1) Club search -> show all its players (values from Spieler)
            clubs = db_read("SELECT teamnr, name FROM Clubs WHERE name LIKE %s", (like,))
            if clubs:
                teamnrs = [c["teamnr"] for c in clubs]
                placeholders = ",".join(["%s"] * len(teamnrs))

                club_players = db_read(
                    f"""
                    SELECT C.name AS club, S.spielernr, S.team, S.vorname, S.nachname, S.position,
                           S.tore, S.vorlagen, S.marktwert
                    FROM Spieler S
                    JOIN Clubs C ON C.teamnr = S.team
                    WHERE S.team IN ({placeholders})
                    ORDER BY C.name, S.nachname, S.vorname
                    """,
                    tuple(teamnrs),
                )

            # 2) Player search (may return multiple if same name)
            player_rows = db_read(
                """
                SELECT C.name AS club, S.spielernr, S.team, S.vorname, S.nachname, S.position,
                       S.tore, S.vorlagen, S.marktwert
                FROM Spieler S
                JOIN Clubs C ON C.teamnr = S.team
                WHERE CONCAT(S.vorname, ' ', S.nachname) LIKE %s
                   OR S.vorname LIKE %s
                   OR S.nachname LIKE %s
                ORDER BY S.nachname, S.vorname, C.name
                """,
                (like, like, like),
            )

            # 3) Coach search (may return multiple if same name)
            coach_rows = db_read(
                """
                SELECT C.name AS club, T.trainernr, T.team, T.vorname, T.nachname
                FROM Cheftrainer T
                JOIN Clubs C ON C.teamnr = T.team
                WHERE CONCAT(T.vorname, ' ', T.nachname) LIKE %s
                   OR T.vorname LIKE %s
                   OR T.nachname LIKE %s
                ORDER BY T.nachname, T.vorname, C.name
                """,
                (like, like, like),
            )

            # 4) League search -> show teams ordered by platzierung + the league country
            league_teams = db_read(
                """
                SELECT L.name AS liga, L.land, C.platzierung, C.name AS club, C.tore, C.gegentore
                FROM Liga L
                JOIN Clubs C ON C.liga = L.liganr
                WHERE L.name LIKE %s
                ORDER BY C.platzierung ASC, C.name
                """,
                (like,),
            )

    return render_template(
        "dbexplorer.html",
        q=q,
        club_players=club_players,
        player_rows=player_rows,
        coach_rows=coach_rows,
        league_teams=league_teams,
    )




#admin
import transfermarktimport  # make sure the file is importable (transfermarktimport.py next to flask_app.py)

def admin_required():
    """Small guard: user must be logged in AND admin session must be active."""
    return session.get("is_admin") is True


def execute_sql_script(sql_text: str):
    """
    Execute a SQL script containing multiple statements (generated by transfermarktimport.build_sql()).
    Your db_write() executes only one statement, so we need a multi-statement runner.
    """
    conn = get_conn()
    try:
        cur = conn.cursor()
        # naive split is OK here because the generated SQL is predictable (no semicolons inside values)
        statements = [s.strip() for s in sql_text.split(";") if s.strip()]
        for stmt in statements:
            cur.execute(stmt)
        conn.commit()
    finally:
        try:
            cur.close()
        except:
            pass
        conn.close()


def empty_transfermarkt_tables():
    """
    IMPORTANT: empty Clubs, Cheftrainer, Spieler, Liga before importing.
    Use FK checks off + TRUNCATE to reset AUTO_INCREMENT.
    """
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SET FOREIGN_KEY_CHECKS=0;")
        # order matters with FKs
        cur.execute("TRUNCATE TABLE Spieler;")
        cur.execute("TRUNCATE TABLE Cheftrainer;")
        cur.execute("TRUNCATE TABLE Clubs;")
        cur.execute("TRUNCATE TABLE Liga;")
        cur.execute("SET FOREIGN_KEY_CHECKS=1;")
        conn.commit()
    finally:
        try:
            cur.close()
        except:
            pass
        conn.close()


@app.route("/adminlogin", methods=["GET", "POST"])
def adminlogin():
    # NEW: if not logged in normally, go to normal login first (with next)
    if not current_user.is_authenticated:
        return redirect(url_for("login", next=url_for("adminlogin")))

    error = None

    # already admin? go straight in
    if session.get("is_admin"):
        return redirect(url_for("adminarea"))

    if request.method == "POST":
        pw = request.form.get("admin_password", "")
        if pw == ADMIN_PASSWORD:
            session["is_admin"] = True
            return redirect(url_for("adminarea"))
        error = "Admin-Passwort ist falsch."

    return render_template("admin_login.html", error=error)


@app.route("/adminlogout", methods=["POST"])
def adminlogout():
    if not current_user.is_authenticated:
        return redirect(url_for("login", next=url_for("index")))
    session.pop("is_admin", None)
    return redirect(url_for("index"))


@app.route("/adminarea", methods=["GET", "POST"])
def adminarea():
    # NEW: require normal login first
    if not current_user.is_authenticated:
        return redirect(url_for("login", next=url_for("adminarea")))

    # NEW: require admin session flag
    if not admin_required():
        return redirect(url_for("adminlogin"))

    message = None
    error = None

    q = ""
    results = {
        "Liga": [],
        "Clubs": [],
        "Spieler": [],
        "Cheftrainer": [],
    }

    def do_search(query: str):
        """Search across all 4 tables (text + numeric via CAST)"""
        like = f"%{query}%"

        # Liga
        liga_rows = db_read(
            """
            SELECT liganr, name, land
            FROM Liga
            WHERE CAST(liganr AS CHAR) LIKE %s
               OR name LIKE %s
               OR land LIKE %s
            ORDER BY liganr
            """,
            (like, like, like),
        )

        # Clubs
        clubs_rows = db_read(
            """
            SELECT teamnr, liga, tore, gegentore, name, platzierung
            FROM Clubs
            WHERE CAST(teamnr AS CHAR) LIKE %s
               OR CAST(liga AS CHAR) LIKE %s
               OR CAST(tore AS CHAR) LIKE %s
               OR CAST(gegentore AS CHAR) LIKE %s
               OR name LIKE %s
               OR CAST(platzierung AS CHAR) LIKE %s
            ORDER BY teamnr
            """,
            (like, like, like, like, like, like),
        )

        # Spieler
        spieler_rows = db_read(
            """
            SELECT spielernr, team, vorname, nachname, tore, vorlagen, marktwert, position
            FROM Spieler
            WHERE CAST(spielernr AS CHAR) LIKE %s
               OR CAST(team AS CHAR) LIKE %s
               OR vorname LIKE %s
               OR nachname LIKE %s
               OR CAST(tore AS CHAR) LIKE %s
               OR CAST(vorlagen AS CHAR) LIKE %s
               OR CAST(marktwert AS CHAR) LIKE %s
               OR position LIKE %s
            ORDER BY spielernr
            """,
            (like, like, like, like, like, like, like, like),
        )

        # Cheftrainer
        coach_rows = db_read(
            """
            SELECT trainernr, team, vorname, nachname
            FROM Cheftrainer
            WHERE CAST(trainernr AS CHAR) LIKE %s
               OR CAST(team AS CHAR) LIKE %s
               OR vorname LIKE %s
               OR nachname LIKE %s
            ORDER BY trainernr
            """,
            (like, like, like, like),
        )

        return liga_rows, clubs_rows, spieler_rows, coach_rows

    if request.method == "POST":
        action = request.form.get("action", "")

        # 1) run import
        if action == "import":
            try:
                empty_transfermarkt_tables()
                sql_text = transfermarktimport.build_sql()
                execute_sql_script(sql_text)
                message = "Import erfolgreich: Tabellen geleert und Transfermarkt-Daten importiert."
            except Exception as e:
                error = f"Import fehlgeschlagen: {e}"

        # 2) search
        elif action == "search":
            q = (request.form.get("q") or "").strip()
            if q:
                liga_rows, clubs_rows, spieler_rows, coach_rows = do_search(q)
                results["Liga"] = liga_rows
                results["Clubs"] = clubs_rows
                results["Spieler"] = spieler_rows
                results["Cheftrainer"] = coach_rows

        # 3) update a single row
        elif action == "update":
            table = request.form.get("table")
            pk_name = request.form.get("pk_name")
            pk_value = request.form.get("pk_value")
            q = (request.form.get("q") or "").strip()

            # Whitelist editable columns per table (protect against SQL injection)
            allowed = {
                "Liga": ( "name", "land" ),
                "Clubs": ( "liga", "tore", "gegentore", "name", "platzierung" ),
                "Spieler": ( "team", "vorname", "nachname", "tore", "vorlagen", "marktwert", "position" ),
                "Cheftrainer": ( "team", "vorname", "nachname" ),
            }
            pk_map = {
                "Liga": "liganr",
                "Clubs": "teamnr",
                "Spieler": "spielernr",
                "Cheftrainer": "trainernr",
            }

            try:
                if table not in allowed or pk_map.get(table) != pk_name:
                    raise ValueError("Ungültige Update-Anfrage.")

                # build SET clause from posted fields
                sets = []
                params = []
                for col in allowed[table]:
                    if col in request.form:
                        sets.append(f"{col}=%s")
                        params.append(request.form.get(col))

                if not sets:
                    raise ValueError("Keine Felder zum Speichern gefunden.")

                params.append(pk_value)
                sql = f"UPDATE {table} SET {', '.join(sets)} WHERE {pk_name}=%s"
                db_write(sql, tuple(params))

                message = f"{table} ({pk_name}={pk_value}) gespeichert."

                # re-run search so the user still sees results
                if q:
                    liga_rows, clubs_rows, spieler_rows, coach_rows = do_search(q)
                    results["Liga"] = liga_rows
                    results["Clubs"] = clubs_rows
                    results["Spieler"] = spieler_rows
                    results["Cheftrainer"] = coach_rows

            except Exception as e:
                error = f"Speichern fehlgeschlagen: {e}"

        # ============================
        # delete a row
        # ============================
        elif action == "delete":
            table = request.form.get("table")
            pk_name = request.form.get("pk_name")
            pk_value = request.form.get("pk_value")
            q = (request.form.get("q") or "").strip()

            pk_map = {
                "Liga": "liganr",
                "Clubs": "teamnr",
                "Spieler": "spielernr",
                "Cheftrainer": "trainernr",
            }

            try:
                if table not in pk_map or pk_map.get(table) != pk_name:
                    raise ValueError("Ungültige Delete-Anfrage.")

                db_write(f"DELETE FROM {table} WHERE {pk_name}=%s", (pk_value,))
                message = f"{table} ({pk_name}={pk_value}) gelöscht."

                if q:
                    liga_rows, clubs_rows, spieler_rows, coach_rows = do_search(q)
                    results["Liga"] = liga_rows
                    results["Clubs"] = clubs_rows
                    results["Spieler"] = spieler_rows
                    results["Cheftrainer"] = coach_rows

            except Exception as e:
                error = f"Löschen fehlgeschlagen: {e}"

        # ============================
        # insert a row  (FIXED INDENT)
        # ============================
        elif action == "insert":
            table = request.form.get("table")
            q = (request.form.get("q") or "").strip()

            # AUTO_INCREMENT PKs: wir insertieren OHNE PK-Spalte
            allowed_insert = {
                "Liga": ("name", "land"),
                "Clubs": ("liga", "tore", "gegentore", "name", "platzierung"),
                "Spieler": ("team", "vorname", "nachname", "tore", "vorlagen", "marktwert", "position"),
                "Cheftrainer": ("team", "vorname", "nachname"),
            }

            try:
                if table not in allowed_insert:
                    raise ValueError("Ungültige Tabelle für Insert.")

                cols = allowed_insert[table]
                values = [request.form.get(c) for c in cols]

                # Basic int cleanup for numeric fields
                int_fields = {
                    "Clubs": ("liga", "tore", "gegentore", "platzierung"),
                    "Spieler": ("team", "tore", "vorlagen", "marktwert"),
                    "Cheftrainer": ("team",),
                }
                for i, col in enumerate(cols):
                    if col in int_fields.get(table, ()):
                        if values[i] in (None, ""):
                            values[i] = 0
                        values[i] = int(values[i])

                # Pflichtfelder (sehr minimal)
                if table == "Liga" and (not values[0] or not values[1]):
                    raise ValueError("Liga: name und land sind Pflicht.")
                if table == "Clubs" and (not request.form.get("name") or not request.form.get("liga")):
                    raise ValueError("Clubs: name und liga sind Pflicht.")
                if table == "Spieler" and (not request.form.get("vorname") or not request.form.get("team")):
                    raise ValueError("Spieler: vorname und team sind Pflicht.")
                if table == "Cheftrainer" and (not request.form.get("vorname") or not request.form.get("team")):
                    raise ValueError("Cheftrainer: vorname und team sind Pflicht.")

                placeholders = ", ".join(["%s"] * len(cols))
                col_sql = ", ".join(cols)
                sql = f"INSERT INTO {table} ({col_sql}) VALUES ({placeholders})"

                db_write(sql, tuple(values))
                message = f"Neue Zeile in {table} eingefügt."

                # Immer danach Ergebnisse aktualisieren:
                if q:
                    liga_rows, clubs_rows, spieler_rows, coach_rows = do_search(q)
                    results["Liga"] = liga_rows
                    results["Clubs"] = clubs_rows
                    results["Spieler"] = spieler_rows
                    results["Cheftrainer"] = coach_rows
                else:
                    # show something so user sees "it happened"
                    results[table] = db_read(f"SELECT * FROM {table} ORDER BY 1 DESC LIMIT 25", ())

            except Exception as e:
                error = f"Einfügen fehlgeschlagen: {e}"
                logging.exception("Insert failed")



    return render_template("admin_area.html", message=message, error=error, q=q, results=results)





if __name__ == "__main__":
    app.run()
