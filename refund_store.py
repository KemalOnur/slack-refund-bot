import os, sqlite3


DB_URL = os.getenv("DATABASE_URL", "sqlite:///local.db")
DB_PATH = DB_URL.replace("sqlite:///","") if DB_URL.startswith("sqlite:///") else DB_URL


def _conn():
    conn = sqlite3.connect(DB_PATH, timeout=5.0)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn

def init_db():
    with _conn() as c:
        c.execute("PRAGMA busy_timeout=5000;")
        c.execute("""
        CREATE TABLE IF NOT EXISTS refund_requests (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          order_id TEXT NOT NULL,
          amount REAL NOT NULL,
          currency TEXT NOT NULL,
          reason TEXT,
          status TEXT NOT NULL,
          requested_by TEXT,
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")

def insert_refund(order_id:str, amount:float, currency:str, reason:str, requested_by:str) ->int:
    with _conn() as c:
        cur = c.execute(
            "INSERT INTO refund_requests(order_id,amount,currency,reason,status,requested_by) VALUES (?,?,?,?,?,?)",
            (order_id, amount, currency, reason, "PENDING", requested_by)
        )
        return cur.lastrowid
    

def update_status(req_id:int, status:str, approver_id:str|None=None):
    with _conn() as c:
        c.execute("UPDATE refund_requests SET status=?, requested_by=COALESCE(requested_by, requested_by) WHERE id=?", (status,req_id))


def get_refund(req_id:int):
    with _conn() as c:
        cur = c.execute("SELECT id, order_id, amount, currency, status FROM refund_requests WHERE id=?", (req_id,))
        return cur.fetchone()