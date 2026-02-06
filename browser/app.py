from flask import Flask, render_template, request
import sqlite3

app = Flask(__name__)
DB_PATH = "universe.db"


def get_tables():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r[0] for r in cur.fetchall()]
    conn.close()
    return tables


def run_query(sql):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(sql)
    rows = cur.fetchall()
    columns = rows[0].keys() if rows else []
    conn.close()
    return columns, rows


@app.route("/", methods=["GET", "POST"])
def index():
    query = "SELECT * FROM regions LIMIT 50;"
    columns, rows = [], []
    error = None

    if request.method == "POST":
        query = request.form["query"]
        try:
            columns, rows = run_query(query)
        except Exception as e:
            error = str(e)

    return render_template(
        "index.html",
        tables=get_tables(),
        query=query,
        columns=columns,
        rows=rows,
        error=error
    )


if __name__ == "__main__":
    app.run(debug=True)
