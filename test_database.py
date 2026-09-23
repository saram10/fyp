"""
tests/test_database.py
Pytest suite for database.py. Every test runs against a fresh, temporary
SQLite file (never the real expense_tracker.db), via the `db` fixture below.

Run with:  pytest
"""
import sys
import os
import sqlite3
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import database


@pytest.fixture
def db(tmp_path, monkeypatch):
    """Points database.DB_PATH at a fresh temp file for the duration of one test."""
    test_db_path = str(tmp_path / "test_expense_tracker.db")
    monkeypatch.setattr(database, "DB_PATH", test_db_path)
    database.init_db()
    return database


# ---------------- Initialization ----------------

def test_init_db_creates_expected_tables(db):
    with db.get_conn() as conn:
        rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    table_names = {r["name"] for r in rows}
    assert {"transactions", "categories", "budgets", "settings"}.issubset(table_names)


def test_init_db_seeds_default_categories(db):
    expense_cats = db.get_categories("Expense")
    income_cats = db.get_categories("Income")
    assert len(expense_cats) > 0
    assert len(income_cats) > 0
    assert any(c["name"] == "Groceries" for c in expense_cats)
    assert any(c["name"] == "Sales" for c in income_cats)


def test_init_db_seeds_default_settings(db):
    assert db.get_setting("currency") == "$"
    assert db.get_setting("business_name") == "My Business"


def test_init_db_is_idempotent(db):
    # Calling init_db() again should not duplicate categories or raise errors.
    before = len(db.get_categories())
    db.init_db()
    after = len(db.get_categories())
    assert before == after


# ---------------- Transactions ----------------

def test_add_transaction_inserts_row(db):
    db.add_transaction("2026-06-01", "Income", "Sales", 500, "Cash", "Walk-in", "Daily sales")
    df = db.get_transactions_df()
    assert len(df) == 1
    row = df.iloc[0]
    assert row["type"] == "Income"
    assert row["category"] == "Sales"
    assert row["amount"] == 500


def test_get_transactions_df_empty_when_no_data(db):
    df = db.get_transactions_df()
    assert df.empty


def test_get_transactions_df_sorted_by_date_desc(db):
    db.add_transaction("2026-01-01", "Expense", "Rent", 100, "Cash", "", "")
    db.add_transaction("2026-06-01", "Expense", "Rent", 100, "Cash", "", "")
    df = db.get_transactions_df()
    dates = df["date"].tolist()
    assert dates == sorted(dates, reverse=True)


def test_update_transaction_changes_values(db):
    db.add_transaction("2026-06-01", "Expense", "Groceries", 50, "Cash", "Vendor A", "")
    tid = int(db.get_transactions_df().iloc[0]["id"])
    db.update_transaction(tid, "2026-06-01", "Expense", "Groceries", 120, "Cash", "Vendor A", "restock")
    df = db.get_transactions_df()
    assert df.iloc[0]["amount"] == 120
    assert df.iloc[0]["description"] == "restock"


def test_delete_transaction_removes_row(db):
    db.add_transaction("2026-06-01", "Expense", "Rent", 300, "Bank Transfer", "", "")
    db.add_transaction("2026-06-02", "Income", "Sales", 700, "Cash", "", "")
    tid_to_delete = int(db.get_transactions_df().iloc[0]["id"])
    db.delete_transaction(tid_to_delete)
    df = db.get_transactions_df()
    assert len(df) == 1
    assert tid_to_delete not in df["id"].tolist()


def test_delete_transactions_bulk(db):
    for i in range(5):
        db.add_transaction(f"2026-06-0{i+1}", "Expense", "Rent", 100, "Cash", "", "")
    df = db.get_transactions_df()
    ids_to_delete = df["id"].tolist()[:3]
    db.delete_transactions(ids_to_delete)
    remaining = db.get_transactions_df()
    assert len(remaining) == 2
    assert not set(ids_to_delete) & set(remaining["id"].tolist())


def test_delete_transactions_empty_list_is_noop(db):
    db.add_transaction("2026-06-01", "Income", "Sales", 100, "Cash", "", "")
    db.delete_transactions([])
    assert len(db.get_transactions_df()) == 1


# ---------------- Categories ----------------

def test_add_category_new_appears_in_list(db):
    db.add_category("Pet Supplies", "Expense", "🐾")
    cats = [c["name"] for c in db.get_categories("Expense")]
    assert "Pet Supplies" in cats


def test_add_category_duplicate_is_ignored(db):
    before = len(db.get_categories("Expense"))
    db.add_category("Groceries", "Expense")  # already exists from defaults
    after = len(db.get_categories("Expense"))
    assert before == after


def test_delete_category_removes_it(db):
    db.add_category("Temp Category", "Expense")
    db.delete_category("Temp Category")
    cats = [c["name"] for c in db.get_categories("Expense")]
    assert "Temp Category" not in cats


# ---------------- Budgets ----------------

def test_set_budget_creates_new_budget(db):
    db.set_budget("Groceries", 200)
    budgets = db.get_budgets()
    assert len(budgets) == 1
    assert budgets[0]["category"] == "Groceries"
    assert budgets[0]["monthly_limit"] == 200


def test_set_budget_upserts_not_duplicates(db):
    db.set_budget("Groceries", 150)
    db.set_budget("Groceries", 200)
    budgets = db.get_budgets()
    assert len(budgets) == 1
    assert budgets[0]["monthly_limit"] == 200


def test_delete_budget_removes_it(db):
    db.set_budget("Rent", 500)
    db.delete_budget("Rent")
    assert db.get_budgets() == []


# ---------------- Settings ----------------

def test_get_setting_returns_default_when_missing(db):
    assert db.get_setting("nonexistent_key", "fallback") == "fallback"


def test_set_setting_then_get_setting(db):
    db.set_setting("currency", "Rs.")
    assert db.get_setting("currency") == "Rs."


def test_set_setting_overwrites_existing(db):
    db.set_setting("business_name", "First Name")
    db.set_setting("business_name", "Second Name")
    assert db.get_setting("business_name") == "Second Name"


# ---------------- PIN Lock ----------------

def test_has_pin_false_by_default(db):
    assert db.has_pin() is False


def test_set_pin_enables_has_pin(db):
    db.set_pin("1234")
    assert db.has_pin() is True


def test_verify_pin_correct(db):
    db.set_pin("4321")
    assert db.verify_pin("4321") is True


def test_verify_pin_incorrect(db):
    db.set_pin("4321")
    assert db.verify_pin("0000") is False


def test_verify_pin_when_none_set(db):
    assert db.verify_pin("anything") is False


def test_remove_pin_disables_lock(db):
    db.set_pin("1111")
    db.remove_pin()
    assert db.has_pin() is False
    assert db.verify_pin("1111") is False


def test_pin_hash_is_not_plaintext(db):
    db.set_pin("1234")
    stored_hash = db.get_setting("pin_hash")
    assert stored_hash != "1234"
    assert len(stored_hash) == 64  # sha256 hex digest length


def test_different_pins_produce_different_hashes(db):
    db.set_pin("1111")
    hash_a = db.get_setting("pin_hash")
    db.set_pin("2222")
    hash_b = db.get_setting("pin_hash")
    assert hash_a != hash_b


# ---------------- Backup & Restore ----------------

def test_export_db_bytes_returns_data(db):
    db.add_transaction("2026-06-01", "Income", "Sales", 500, "Cash", "", "")
    data = db.export_db_bytes()
    assert isinstance(data, bytes)
    assert len(data) > 0


def test_export_then_import_round_trip(db, tmp_path, monkeypatch):
    db.add_transaction("2026-06-01", "Income", "Sales", 999, "Cash", "", "round-trip test")
    backup = db.export_db_bytes()

    # Point at a brand-new empty database, then restore the backup into it.
    new_path = str(tmp_path / "restored.db")
    monkeypatch.setattr(database, "DB_PATH", new_path)
    database.init_db()
    assert db.get_transactions_df().empty  # fresh db, no data yet

    success, message = db.import_db_bytes(backup)
    assert success is True
    df = db.get_transactions_df()
    assert len(df) == 1
    assert df.iloc[0]["description"] == "round-trip test"


def test_import_db_bytes_rejects_invalid_file(db):
    success, message = db.import_db_bytes(b"not a real sqlite file")
    assert success is False
    assert "valid" in message.lower()


def test_import_db_bytes_rejects_wrong_schema(db, tmp_path):
    # A real SQLite file, but missing the expected tables.
    bogus_path = tmp_path / "bogus.db"
    conn = sqlite3.connect(str(bogus_path))
    conn.execute("CREATE TABLE unrelated_table (id INTEGER)")
    conn.commit()
    conn.close()
    with open(bogus_path, "rb") as f:
        data = f.read()

    success, message = db.import_db_bytes(data)
    assert success is False
    assert "backup" in message.lower()


def test_import_db_bytes_creates_backup_file(db):
    db.add_transaction("2026-06-01", "Income", "Sales", 500, "Cash", "", "")
    original_backup = db.export_db_bytes()
    db.import_db_bytes(original_backup)
    assert os.path.exists(database.DB_PATH + ".bak")
