import os
import time
import sqlite3
from flask import Flask, render_template, request

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DB_PATH = os.environ.get(
    "EF_DB_PATH",
    os.path.abspath(os.path.join(BASE_DIR, "..", "db", "eve_universe.db")),
)

app = Flask(__name__, template_folder="templates", static_folder=".", static_url_path="")


def list_tables(db_path):
    with sqlite3.connect(db_path) as conn:
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        return [r[0] for r in cur.fetchall()]


def run_query(db_path, sql):
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(sql)
        rows = cur.fetchall()
        columns = [d[0] for d in cur.description] if cur.description else []
        return columns, rows, cur.rowcount


@app.route("/", methods=["GET", "POST"])
def index():
    query = "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;"
    columns, rows, rowcount = [], [], None
    error = None
    db_error = None
    elapsed_ms = None

    db_path = request.form.get("db_path") or request.args.get("db_path") or DEFAULT_DB_PATH

    if request.method == "POST":
        submitted_query = request.form.get("query")
        if submitted_query:
            query = submitted_query
            try:
                start = time.perf_counter()
                columns, rows, rowcount = run_query(db_path, query)
                elapsed_ms = int((time.perf_counter() - start) * 1000)
            except Exception as e:
                error = str(e)

    try:
        tables = list_tables(db_path)
    except Exception as e:
        tables = []
        db_error = str(e)

    return render_template(
        "index.html",
        tables=tables,
        db_path=db_path,
        db_error=db_error,
        query=query,
        columns=columns,
        rows=rows,
        rowcount=rowcount,
        elapsed_ms=elapsed_ms,
        error=error,
    )


if __name__ == "__main__":
    app.run(debug=True)
