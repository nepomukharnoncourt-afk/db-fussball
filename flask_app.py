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
    # Get DB name from env (same one db.py uses)
    db_name = os.getenv("DB_DATABASE")

    # All available tables in this database
    table_rows = db_read(
        """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = %s
        ORDER BY table_name
        """,
        (db_name,),
    )
    available_tables = [r["table_name"] for r in table_rows]
    allowed = set(available_tables)

    selected_tables = []
    bad_tables = []
    limit = 50

    if request.method == "POST":
        # limit
        limit_raw = (request.form.get("limit") or "50").strip()
        try:
            limit = int(limit_raw)
        except ValueError:
            limit = 50
        limit = max(1, min(limit, 500))  # clamp 1..500

        # selected via checkboxes
        selected_tables.extend(request.form.getlist("tables"))

        # selected via manual text field
        manual = (request.form.get("table_name") or "").strip()
        if manual:
            selected_tables.append(manual)

        # normalize + dedupe while preserving order
        cleaned = []
        seen = set()
        for t in selected_tables:
            t = (t or "").strip()
            if not t or t in seen:
                continue
            seen.add(t)
            cleaned.append(t)
        selected_tables = cleaned

    # whitelist validation
    bad_tables = [t for t in selected_tables if t not in allowed]
    selected_tables = [t for t in selected_tables if t in allowed]

    # Fetch data for selected tables
    table_data = {}   # table -> list[dict]
    table_cols = {}   # table -> list[str]

    for t in selected_tables:
        # Safe because:
        # - t is whitelisted from information_schema
        # - limit is an int we clamp
        rows = db_read(f"SELECT * FROM `{t}` LIMIT {limit}")

        if rows:
            cols = list(rows[0].keys())
        else:
            # If empty, still show column headers
            desc = db_read(f"DESCRIBE `{t}`")
            cols = [d["Field"] for d in desc]

        table_data[t] = rows
        table_cols[t] = cols

    return render_template(
        "dbexplorer.html",
        available_tables=available_tables,
        selected_tables=selected_tables,
        bad_tables=bad_tables,
        limit=limit,
        table_data=table_data,
        table_cols=table_cols,
    )




if __name__ == "__main__":
    app.run()
