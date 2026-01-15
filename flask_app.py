from flask import Flask, redirect, render_template, request, url_for
from dotenv import load_dotenv
import os
import git
import hmac
import hashlib
from db import db_read, db_write
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
@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    # GET
    if request.method == "GET":
        todos = db_read("SELECT id, content, due FROM todos WHERE user_id=%s ORDER BY due", (current_user.id,))
        return render_template("main_page.html", todos=todos)

    # POST
    content = request.form["contents"]
    due = request.form["due_at"]
    db_write("INSERT INTO todos (user_id, content, due) VALUES (%s, %s, %s)", (current_user.id, content, due, ))
    return redirect(url_for("index"))

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





if __name__ == "__main__":
    app.run()
