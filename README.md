# 💰 Expense Tracker

A beautiful, full-featured expense & income tracker for personal use or small shop owners — built with Python, Streamlit, Plotly, and SQLite.

## Features

- **📊 Dashboard** — colorful KPI cards (income, expenses, balance, transaction count), a date-range filter, pie chart of spending by category, income-vs-expense trend area chart, top expense categories, and payment-method breakdown.
- **➕ Add Transaction** — quick form for logging income or expenses, with category icons, payment method, customer/vendor name, and notes. Add custom categories on the fly.
- **📒 Transactions** — full searchable/filterable table (by type, category, date range, keyword) with inline editing, bulk delete, and CSV export.
- **🎯 Budgets** — set a monthly spending limit per category and see live progress bars with over-budget warnings — great for shop owners tracking stock/rent/wage limits.
- **📈 Reports** — monthly income vs expense bars, cumulative net balance over time, a category-spending heatmap by month, and an all-time category leaderboard.
- **💬 Help & FAQ** — a simple built-in chatbot that answers common "how do I..." questions (adding transactions, budgets, exporting, privacy, etc.). It's rule-based and works fully offline — no API key or internet connection needed.
- **⚙️ Settings** — set your business name and currency symbol, an optional PIN lock, one-click backup/restore, and a safe "wipe all data" option.
- **🌙 Dark Mode** — toggle from the sidebar any time; the setting is remembered.
- **🔒 PIN Lock** — optionally require a PIN before the app opens, useful for a shared shop computer or tablet. Set it up under Settings → App Lock.
- **💾 Backup & Restore** — download your entire database as a single file, or restore from a previous backup, under Settings → Backup & Restore.

All data is stored locally in a SQLite file in your user folder (`~/ExpenseTrackerData/expense_tracker.db` — e.g. `C:\Users\YourName\ExpenseTrackerData\expense_tracker.db` on Windows) — nothing leaves your computer.

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
   (If you're on a system that requires it: `pip install -r requirements.txt --break-system-packages`)

2. Run the app:
   ```bash
   streamlit run app.py
   ```

3. Your browser will open automatically at `http://localhost:8501`. If not, click the link shown in the terminal.

## Package it as a standalone Windows app (no Python needed for recipients)

Want to send this to someone who should just double-click a file and have it work, with no Python, no terminal, no commands? You can build a single `ExpenseTracker.exe` that does exactly that.

**This is a one-time step you (or anyone with Python) does once.** The people you send the `.exe` to afterward don't install or run anything else.

1. On a Windows PC with Python installed, put the whole project folder there (needs `app.py`, `database.py`, `desktop_launcher.py`, `icon.ico`, `requirements.txt`, and `build_windows_exe.bat` all in the same folder).
2. Double-click **`build_windows_exe.bat`**. It installs the needed packages and builds the app — this can take several minutes, especially the first time.
3. When it finishes, you'll have `dist\ExpenseTracker.exe`. That single file is the whole app — send that file to anyone. Double-clicking it opens ExpenseTracker in their default browser, fully offline, with their own private data folder.

A few notes on the packaged version:
- The first launch is a bit slower than later ones (it's unpacking itself into a temp folder each time) — that's normal for this kind of single-file app.
- A console window appears alongside the browser tab — that's expected, it's how the app runs in the background; closing that window closes the app.
- Windows Defender or another antivirus may flag a brand-new unsigned `.exe` the first time — this is common for small, unsigned apps and not a sign anything is wrong. Choosing "More info → Run anyway" (or adding an exclusion) resolves it.
- Each person who runs it gets their **own** local data folder on their own PC (`~/ExpenseTrackerData/`) — it's not shared or synced between computers.

## Tips

- The first time you run it, default categories (Groceries, Rent, Sales, Salary, etc.) are pre-loaded — you can delete or add your own anytime from the **Add Transaction** page.
- For a small shop: log each sale as an "Income → Sales" entry, and use the **Party** field to note the customer if relevant. Track stock purchases under "Inventory / Stock" and set a monthly budget for it.
- Use **Reports → Category Trend Heatmap** to spot which expense categories are creeping up month over month.
- Your database file lives at `~/ExpenseTrackerData/expense_tracker.db` and can be backed up by simply copying it, or use **Settings → Backup & Restore** for a guided download/upload flow.
- If you forget your PIN, you can still recover your data: close the app, delete (or rename) `expense_tracker.db` inside your `ExpenseTrackerData` folder, and restart — this clears the PIN along with all data, so restore from a backup file afterward if you have one.

## Running the tests

The `database.py` module (all data logic) has a full pytest suite in `tests/test_database.py`, covering transactions, categories, budgets, settings, the PIN lock, and backup/restore. It runs against a temporary database, never your real data.

```bash
pytest
```

Enjoy tracking! 🎉
