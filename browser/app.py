import csv
import json
import os
import time
import io
import sqlite3
from flask import Flask, render_template, request, jsonify, Response
from werkzeug.utils import secure_filename
try:
    # tkinter is used to open a native file dialog on the server (localhost)
    from tkinter import Tk, filedialog
except Exception:
    Tk = None
    filedialog = None
import sys
import subprocess

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DB_PATH = os.environ.get(
    "EF_DB_PATH",
    os.path.abspath(os.path.join(BASE_DIR, "..", "db", "eve_universe.db")),
)

app = Flask(__name__, template_folder=".", static_folder=".", static_url_path="/static")
STORE_PATH = os.path.join(BASE_DIR, "saved_queries.json")

MAX_HISTORY = 100
DEFAULT_PAGE_SIZE = 2000


def resolve_db_path(db_path):
    if not db_path:
        return db_path
    if os.path.isabs(db_path):
        return db_path
    candidate = os.path.abspath(os.path.join(BASE_DIR, "..", "db", db_path))
    if os.path.exists(candidate):
        return candidate
    return db_path


def list_tables(db_path):
    with sqlite3.connect(db_path) as conn:
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        return [r[0] for r in cur.fetchall()]
@app.route("/api/upload_db", methods=["GET", "POST", "OPTIONS"])
@app.route("/upload_db", methods=["GET", "POST", "OPTIONS"])
def upload_db():
    """Accept a database file upload and save it into the repo db/ folder.

    For debugging this endpoint will also respond to GET requests with a
    small informational JSON. Successful POST returns {"name": "<saved-filename>"}.
    """
    # Log incoming method/path for debugging (visible in the server terminal)
    try:
        print(f"[upload_db] {request.method} {request.path}")
    except Exception:
        pass

    if request.method != "POST":
        return jsonify({"message": "Upload endpoint: POST a form field 'dbfile'"}), 200

    if "dbfile" not in request.files:
        return jsonify({"error": "No file provided"}), 400
    f = request.files["dbfile"]
    if f.filename == "":
        return jsonify({"error": "Empty filename"}), 400

    filename = secure_filename(f.filename)
    lower = filename.lower()
    if not (lower.endswith(".db") or lower.endswith(".sqlite") or lower.endswith(".sqlite3")):
        return jsonify({"error": "Invalid file type"}), 400

    db_dir = os.path.abspath(os.path.join(BASE_DIR, "..", "db"))
    os.makedirs(db_dir, exist_ok=True)
    # prepend timestamp to avoid collisions
    dest_name = f"uploaded_{int(time.time())}_{filename}"
    dest_path = os.path.join(db_dir, dest_name)
    try:
        f.save(dest_path)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    # Return just the filename; the UI will post this name back and the server
    # will resolve it to the real file under ../db/ to avoid passing absolute
    # filesystem paths through the form.
    return jsonify({"name": dest_name})


@app.route("/choose_db", methods=["POST"])
def choose_db():
    """Open a native file chooser on the server and return the selected path.

    This only works when the server is running locally with GUI access (not
    headless). Returns JSON {"path": "<abs-path>"} or {"canceled": true}.
    """
    # Try tkinter file dialog first if available and environment supports GUI.
    if filedialog:
        try:
            root = Tk()
            root.withdraw()
            path = filedialog.askopenfilename(
                title="Select SQLite database",
                filetypes=[("SQLite DB", "*.db *.sqlite *.sqlite3"), ("All files", "*")],
            )
            root.destroy()
            if not path:
                return jsonify({"canceled": True})
            return jsonify({"path": path})
        except Exception:
            # fall through to other mechanisms
            pass

    # On macOS, try using AppleScript (osascript) to open a native file chooser.
    if sys.platform == "darwin":
        try:
            script = 'set f to choose file with prompt "Select SQLite database"\nPOSIX path of f'
            proc = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
            if proc.returncode != 0:
                # User cancelled or error
                stderr = (proc.stderr or "").strip()
                if stderr:
                    return jsonify({"error": stderr}), 500
                return jsonify({"canceled": True})
            path = proc.stdout.strip()
            if not path:
                return jsonify({"canceled": True})
            return jsonify({"path": path})
        except FileNotFoundError:
            return jsonify({"error": "osascript not found on server"}), 500
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    return jsonify({"error": "server does not have a GUI file dialog available"}), 500


@app.route("/api/check_db", methods=["POST"])
def check_db():
    """Check whether a given filename exists in the server-side db/ folder.

    Expects JSON {"filename": "name.db"} and returns {"exists": bool, "path": "<abs>"}
    """
    try:
        data = request.get_json(force=True)
        filename = data.get("filename") if isinstance(data, dict) else None
    except Exception:
        filename = None
    if not filename:
        return jsonify({"exists": False}), 400
    safe = secure_filename(filename)
    db_dir = os.path.abspath(os.path.join(BASE_DIR, "..", "db"))
    candidate = os.path.join(db_dir, safe)
    if os.path.exists(candidate):
        return jsonify({"exists": True, "path": candidate})
    return jsonify({"exists": False})


def run_query(db_path, sql, params=None):
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(sql, params or ())
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


def clean_select_query(sql):
    cleaned = normalize_query(sql)
    if cleaned.endswith(";"):
        cleaned = cleaned[:-1].rstrip()
    return cleaned


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
    has_next = False
    has_prev = False
    start_row = 0
    end_row = 0
    total_rows = None

    store = load_store()

    db_path = request.form.get("db_path") or request.args.get("db_path") or DEFAULT_DB_PATH

    # If the posted db_path is a filename saved by the upload endpoint, resolve
    # it to the repository `db/` folder so we open the correct file on disk.
    try:
        db_path = resolve_db_path(db_path)
    except Exception:
        pass

    page_size_raw = request.form.get("page_size") or request.args.get("page_size")
    page_raw = request.form.get("page") or request.args.get("page")
    try:
        page_size = int(page_size_raw) if page_size_raw is not None and page_size_raw != "" else DEFAULT_PAGE_SIZE
    except ValueError:
        page_size = DEFAULT_PAGE_SIZE
    try:
        page = int(page_raw) if page_raw is not None and page_raw != "" else 1
    except ValueError:
        page = 1
    if page_size <= 0:
        page_size = DEFAULT_PAGE_SIZE
    if page < 1:
        page = 1

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
                    cleaned = clean_select_query(query)

                    if page_size > 0:
                        offset = (page - 1) * page_size
                        paged_sql = f"SELECT * FROM ({cleaned}) LIMIT ? OFFSET ?"
                        columns, rows, rowcount = run_query(
                            db_path,
                            paged_sql,
                            (page_size + 1, offset),
                        )
                        has_next = len(rows) > page_size
                        if has_next:
                            rows = rows[:page_size]
                        has_prev = page > 1
                        start_row = offset + 1 if rows else 0
                        end_row = offset + len(rows) if rows else 0
                        try:
                            _, count_rows, _ = run_query(
                                db_path,
                                f"SELECT COUNT(*) AS total FROM ({cleaned})",
                            )
                            total_rows = int(count_rows[0][0]) if count_rows else 0
                        except Exception:
                            total_rows = None
                    else:
                        columns, rows, rowcount = run_query(db_path, cleaned)
                        start_row = 1 if rows else 0
                        end_row = len(rows)
                        total_rows = len(rows)
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
        page_size=page_size,
        page=page,
        has_next=has_next,
        has_prev=has_prev,
        start_row=start_row,
        end_row=end_row,
        total_rows=total_rows,
        error=error,
    )


@app.route("/export_csv", methods=["POST"])
def export_csv():
    sql = normalize_query(request.form.get("export_sql"))
    if not sql:
        return "Missing SQL query", 400
    if not is_select_only(sql):
        return "Read-only mode: only SELECT queries are allowed.", 400

    db_path = resolve_db_path(request.form.get("db_path") or DEFAULT_DB_PATH)
    cleaned = clean_select_query(sql)


    def stream_rows():
        with sqlite3.connect(db_path) as conn:
            cur = conn.cursor()
            cur.execute(cleaned)
            headers = [d[0] for d in cur.description] if cur.description else []
            buffer = io.StringIO()
            writer = csv.writer(buffer)
            writer.writerow(headers)
            yield buffer.getvalue()
            buffer.seek(0)
            buffer.truncate(0)
            while True:
                chunk = cur.fetchmany(1000)
                if not chunk:
                    break
                for row in chunk:
                    writer.writerow(row)
                yield buffer.getvalue()
                buffer.seek(0)
                buffer.truncate(0)

    db_name = os.path.splitext(os.path.basename(db_path))[0]
    filename = f"{db_name}_export.csv"
    response = Response(stream_rows(), mimetype="text/csv")
    response.headers["Content-Disposition"] = f"attachment; filename={filename}"
    return response


if __name__ == "__main__":
    app.run(debug=True)
