"""
database.py
Handles all SQLite persistence for the Expense Tracker app.
"""

import sqlite3
import os
import shutil
import hashlib
import secrets
import pandas as pd
from datetime import datetime
from contextlib import contextmanager


def _get_persistent_db_path():
    """
    Returns a stable, writable location for the database file that does NOT
    depend on the app's current working directory. This matters once the app
    is packaged as a standalone .exe: a onefile build runs from a temporary
    extraction folder that gets deleted on exit, so anything saved there
    (or relative to a working directory the packaged app doesn't control)
    would be lost between runs. Storing under the user's home folder keeps
    data safe and in the same place every time, whether run via
    `streamlit run app.py` or as a packaged desktop app.
    """
    home = os.path.expanduser("~")
    data_dir = os.path.join(home, "ExpenseTrackerData")
    os.makedirs(data_dir, exist_ok=True)
    new_path = os.path.join(data_dir, "expense_tracker.db")

    # One-time migration: if someone has an older copy of the app that stored
    # the database next to the source files, bring that data along instead of
    # silently starting fresh.
    legacy_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "expense_tracker.db")
    if not os.path.exists(new_path) and os.path.exists(legacy_path):
        shutil.copy(legacy_path, new_path)

    return new_path


DB_PATH = _get_persistent_db_path()

DEFAULT_EXPENSE_CATEGORIES = [
    ("Groceries", "🛒"), ("Rent", "🏠"), ("Utilities", "💡"),
    ("Transport", "🚗"), ("Food & Dining", "🍔"), ("Inventory / Stock", "📦"),
    ("Staff Wages", "👷"), ("Marketing", "📣"), ("Equipment", "🛠️"),
    ("Health", "💊"), ("Entertainment", "🎬"), ("Education", "📚"),
    ("Insurance", "🛡️"), ("Taxes", "🧾"), ("Miscellaneous", "🔖"),
]

DEFAULT_INCOME_CATEGORIES = [
    ("Sales", "💰"), ("Salary", "💼"), ("Services", "🧰"),
    ("Freelance", "💻"), ("Investment", "📈"), ("Gift", "🎁"),
    ("Refund", "↩️"), ("Other Income", "✨"),
]

PAYMENT_METHODS = ["Cash", "Bank Transfer", "Credit Card", "Debit Card", "Mobile Wallet", "Cheque", "Other"]


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                type TEXT NOT NULL CHECK(type IN ('Income','Expense')),
                category TEXT NOT NULL,
                amount REAL NOT NULL,
                payment_method TEXT,
                party TEXT,
                description TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                type TEXT NOT NULL CHECK(type IN ('Income','Expense')),
                icon TEXT DEFAULT '🔖'
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS budgets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL UNIQUE,
                monthly_limit REAL NOT NULL
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)

        # Seed default categories only if table empty
        c.execute("SELECT COUNT(*) as cnt FROM categories")
        if c.fetchone()["cnt"] == 0:
            for name, icon in DEFAULT_EXPENSE_CATEGORIES:
                c.execute("INSERT OR IGNORE INTO categories (name, type, icon) VALUES (?, 'Expense', ?)", (name, icon))
            for name, icon in DEFAULT_INCOME_CATEGORIES:
                c.execute("INSERT OR IGNORE INTO categories (name, type, icon) VALUES (?, 'Income', ?)", (name, icon))

        # Seed default settings
        c.execute("SELECT COUNT(*) as cnt FROM settings")
        if c.fetchone()["cnt"] == 0:
            c.execute("INSERT INTO settings (key, value) VALUES ('currency', '$')")
            c.execute("INSERT INTO settings (key, value) VALUES ('business_name', 'My Business')")


# ---------------- Transactions ----------------

def add_transaction(date, ttype, category, amount, payment_method, party, description):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO transactions (date, type, category, amount, payment_method, party, description) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (date, ttype, category, amount, payment_method, party, description)
        )


def update_transaction(tid, date, ttype, category, amount, payment_method, party, description):
    with get_conn() as conn:
        conn.execute(
            "UPDATE transactions SET date=?, type=?, category=?, amount=?, payment_method=?, party=?, description=? "
            "WHERE id=?",
            (date, ttype, category, amount, payment_method, party, description, tid)
        )


def delete_transaction(tid):
    with get_conn() as conn:
        conn.execute("DELETE FROM transactions WHERE id=?", (tid,))


def delete_transactions(ids):
    if not ids:
        return
    with get_conn() as conn:
        q = f"DELETE FROM transactions WHERE id IN ({','.join('?' * len(ids))})"
        conn.execute(q, ids)


def get_transactions_df():
    with get_conn() as conn:
        df = pd.read_sql_query("SELECT * FROM transactions ORDER BY date DESC, id DESC", conn)
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])
    return df


# ---------------- Categories ----------------

def get_categories(ttype=None):
    with get_conn() as conn:
        if ttype:
            rows = conn.execute("SELECT * FROM categories WHERE type=? ORDER BY name", (ttype,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM categories ORDER BY type, name").fetchall()
    return [dict(r) for r in rows]


def add_category(name, ttype, icon="🔖"):
    with get_conn() as conn:
        conn.execute("INSERT OR IGNORE INTO categories (name, type, icon) VALUES (?, ?, ?)", (name, ttype, icon))


def delete_category(name):
    with get_conn() as conn:
        conn.execute("DELETE FROM categories WHERE name=?", (name,))


# ---------------- Budgets ----------------

def get_budgets():
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM budgets ORDER BY category").fetchall()
    return [dict(r) for r in rows]


def set_budget(category, monthly_limit):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO budgets (category, monthly_limit) VALUES (?, ?) "
            "ON CONFLICT(category) DO UPDATE SET monthly_limit=excluded.monthly_limit",
            (category, monthly_limit)
        )


def delete_budget(category):
    with get_conn() as conn:
        conn.execute("DELETE FROM budgets WHERE category=?", (category,))


# ---------------- Settings ----------------

def get_setting(key, default=None):
    with get_conn() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return row["value"] if row else default


def set_setting(key, value):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value)
        )


# ---------------- PIN Lock ----------------
# Simple, dependency-free PIN hashing using the standard library (PBKDF2-HMAC-SHA256).
# This is app-level convenience protection (e.g. a shared shop tablet), not bank-grade security.

def _hash_pin(pin, salt_hex):
    salt = bytes.fromhex(salt_hex)
    digest = hashlib.pbkdf2_hmac("sha256", pin.encode("utf-8"), salt, 100_000)
    return digest.hex()


def has_pin():
    """Returns True if a PIN lock is currently enabled."""
    return bool(get_setting("pin_hash", ""))


def set_pin(pin):
    """Creates or overwrites the PIN with a freshly generated salt."""
    salt = secrets.token_hex(16)
    pin_hash = _hash_pin(pin, salt)
    set_setting("pin_salt", salt)
    set_setting("pin_hash", pin_hash)


def verify_pin(pin):
    """Checks a candidate PIN against the stored hash. Returns False if no PIN is set."""
    salt = get_setting("pin_salt", "")
    stored_hash = get_setting("pin_hash", "")
    if not salt or not stored_hash:
        return False
    return _hash_pin(pin, salt) == stored_hash


def remove_pin():
    with get_conn() as conn:
        conn.execute("DELETE FROM settings WHERE key IN ('pin_hash', 'pin_salt')")


# ---------------- Backup & Restore ----------------
# The whole app lives in one SQLite file, so backup/restore is just a validated file copy.

REQUIRED_TABLES = {"transactions", "categories", "budgets", "settings"}


def export_db_bytes():
    """Returns the raw bytes of the current database file, for download."""
    with open(DB_PATH, "rb") as f:
        return f.read()


def import_db_bytes(data):
    """
    Validates and restores a database from raw bytes (e.g. an uploaded backup file).
    The current database is preserved as expense_tracker.db.bak before being replaced.
    Returns (success: bool, message: str).
    """
    tmp_path = DB_PATH + ".upload_tmp"
    with open(tmp_path, "wb") as f:
        f.write(data)

    try:
        test_conn = sqlite3.connect(tmp_path)
        try:
            cur = test_conn.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = {row[0] for row in cur.fetchall()}
        finally:
            test_conn.close()
    except sqlite3.DatabaseError:
        os.remove(tmp_path)
        return False, "That file isn't a valid SQLite database."

    if not REQUIRED_TABLES.issubset(tables):
        os.remove(tmp_path)
        return False, "That file doesn't look like an ExpenseTracker backup (missing expected tables)."

    if os.path.exists(DB_PATH):
        shutil.copy(DB_PATH, DB_PATH + ".bak")
    shutil.move(tmp_path, DB_PATH)
    return True, "Backup restored successfully. Your previous data was saved as expense_tracker.db.bak."
