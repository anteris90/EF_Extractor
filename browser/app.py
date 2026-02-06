import json
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
STORE_PATH = os.path.join(BASE_DIR, "saved_queries.json")

MAX_HISTORY = 100


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


def get_table_columns(db_path, tables):
    schema = {}
    if not tables:
        return schema
    with sqlite3.connect(db_path) as conn:
        for table in tables:
            try:
                cur = conn.execute(f'PRAGMA table_info("{table}")')
                schema[table] = [
                    f"{row[1]} {row[2]}".strip() if row[2] else row[1]
                    for row in cur.fetchall()
                ]
            except sqlite3.Error:
                schema[table] = []
    return schema


def load_store():
    if not os.path.exists(STORE_PATH):
        return {"saved_queries": [], "history": []}
    try:
        with open(STORE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {
            "saved_queries": data.get("saved_queries", []),
            "history": data.get("history", []),
        }
    except (json.JSONDecodeError, OSError):
        return {"saved_queries": [], "history": []}


def save_store(data):
    with open(STORE_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=True, indent=2)


def normalize_query(sql):
    return (sql or "").strip()


def is_select_only(sql):
    cleaned = normalize_query(sql).lower()
    if not cleaned:
        return False
    while cleaned.startswith("--"):
        line_end = cleaned.find("\n")
        if line_end == -1:
            return False
        cleaned = cleaned[line_end + 1 :].lstrip()
    if cleaned.startswith("/*"):
        end_block = cleaned.find("*/")
        if end_block == -1:
            return False
        cleaned = cleaned[end_block + 2 :].lstrip()
    if not cleaned.startswith("select"):
        return False
    semicolon_index = cleaned.find(";")
    if semicolon_index != -1 and semicolon_index != len(cleaned) - 1:
        return False
    return True


def add_history_entry(store, sql):
    history = store.get("history", [])
    sql = normalize_query(sql)
    if not sql:
        return
    history = [q for q in history if q != sql]
    history.insert(0, sql)
    store["history"] = history[:MAX_HISTORY]


@app.route("/", methods=["GET", "POST"])
def index():
    query = "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;"
    columns, rows, rowcount = [], [], None
    error = None
    db_error = None
    elapsed_ms = None

    store = load_store()

    db_path = request.form.get("db_path") or request.args.get("db_path") or DEFAULT_DB_PATH

    if request.method == "POST":
        action = request.form.get("action")
        if action == "clear_history":
            store["history"] = []
            save_store(store)
        elif action == "save_query":
            name = (request.form.get("saved_name") or "").strip()
            notes = (request.form.get("saved_notes") or "").strip()
            sql = normalize_query(request.form.get("saved_sql"))
            saved_id = (request.form.get("saved_id") or "").strip()
            if not name or not sql:
                error = "Saved query requires a name and SQL."
            elif not is_select_only(sql):
                error = "Read-only mode: only SELECT queries can be saved."
            else:
                if saved_id:
                    store["saved_queries"] = [
                        item for item in store["saved_queries"] if str(item.get("id")) != saved_id
                    ]
                    query_id = int(saved_id)
                else:
                    query_id = int(time.time() * 1000)

                store["saved_queries"].insert(
                    0,
                    {
                        "id": query_id,
                        "name": name,
                        "sql": sql,
                        "notes": notes,
                    },
                )
                save_store(store)
        elif action == "delete_saved":
            saved_id = request.form.get("saved_id")
            store["saved_queries"] = [
                item for item in store["saved_queries"] if str(item.get("id")) != str(saved_id)
            ]
            save_store(store)

        submitted_query = request.form.get("query")
        if submitted_query and action not in {"save_query", "delete_saved", "clear_history"}:
            query = submitted_query
            if not is_select_only(query):
                error = "Read-only mode: only SELECT queries are allowed."
            else:
                try:
                    start = time.perf_counter()
                    columns, rows, rowcount = run_query(db_path, query)
                    elapsed_ms = int((time.perf_counter() - start) * 1000)
                    add_history_entry(store, query)
                    save_store(store)
                except Exception as e:
                    error = str(e)

    try:
        tables = list_tables(db_path)
    except Exception as e:
        tables = []
        db_error = str(e)

    table_columns = {}
    if tables:
        try:
            table_columns = get_table_columns(db_path, tables)
        except Exception:
            table_columns = {}

    return render_template(
        "index.html",
        tables=tables,
        table_columns=table_columns,
        saved_queries=store.get("saved_queries", []),
        query_history=store.get("history", []),
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
