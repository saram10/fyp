"""
Expense Tracker — a full-featured personal & small-shop finance app.
Run with:  streamlit run app.py
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date, datetime, timedelta
import io

import database as db

# ----------------------------------------------------------------------------
# PAGE CONFIG & GLOBAL STYLE
# ----------------------------------------------------------------------------
st.set_page_config(
    page_title="Expense Tracker",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
)

db.init_db()

DARK_MODE = db.get_setting("dark_mode", "false") == "true"
PLOTLY_TEMPLATE = "plotly_dark" if DARK_MODE else "plotly_white"

if DARK_MODE:
    THEME = dict(
        bg="#0F1117", card_bg="#1A1D27", text="#E8E8ED", text_muted="#9CA3AF",
        border="#2A2E3A", sidebar_bg="#14161E", input_bg="#1E212C",
    )
else:
    THEME = dict(
        bg="#FFFFFF", card_bg="#FFFFFF", text="#2D3436", text_muted="#636E72",
        border="#EEEEEE", sidebar_bg="#FFFFFF", input_bg="#FFFFFF",
    )

CUSTOM_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"]  {{ font-family: 'Inter', sans-serif; }}

#MainMenu {{visibility: hidden;}}
footer {{visibility: hidden;}}
header {{visibility: hidden;}}

.block-container {{ padding-top: 1.5rem; padding-bottom: 3rem; }}

.stApp {{ background-color: {THEME['bg']}; }}
section[data-testid="stSidebar"] {{ background-color: {THEME['sidebar_bg']}; }}
.stApp, .stMarkdown, p, span, label, .stCaption, div[data-testid="stMarkdownContainer"] {{
    color: {THEME['text']};
}}
div[data-testid="stCaptionContainer"] {{ color: {THEME['text_muted']} !important; }}
div[data-testid="stDataFrame"], div[data-testid="stTable"] {{
    background-color: {THEME['card_bg']};
    border: 1px solid {THEME['border']};
    border-radius: 10px;
}}
.stTextInput input, .stNumberInput input, .stDateInput input, .stSelectbox div[data-baseweb="select"] > div {{
    background-color: {THEME['input_bg']};
    color: {THEME['text']};
}}
hr {{ border-color: {THEME['border']}; margin: 0.6rem 0 1.2rem 0; }}

:root {{
    --accent: #6C5CE7;
    --accent2: #00CEC9;
    --income: #00B894;
    --expense: #FF6B6B;
    --card-bg: #ffffff;
}}

/* KPI Cards */
.kpi-card {{
    background: linear-gradient(135deg, var(--bg1) 0%, var(--bg2) 100%);
    border-radius: 18px;
    padding: 22px 24px;
    color: white;
    box-shadow: 0 8px 24px rgba(0,0,0,0.12);
    position: relative;
    overflow: hidden;
    min-height: 118px;
}}
.kpi-card .icon {{ font-size: 26px; opacity: 0.9; }}
.kpi-card .label {{ font-size: 13px; font-weight: 600; opacity: 0.85; letter-spacing: 0.3px; margin-top: 4px;}}
.kpi-card .value {{ font-size: 28px; font-weight: 800; margin-top: 2px; }}
.kpi-card .sub {{ font-size: 12px; opacity: 0.8; margin-top: 6px; }}

.kpi-income  {{ --bg1: #00B894; --bg2: #00CEC9; }}
.kpi-expense {{ --bg1: #FD5E53; --bg2: #FF8A65; }}
.kpi-balance {{ --bg1: #6C5CE7; --bg2: #A29BFE; }}
.kpi-count   {{ --bg1: #0984E3; --bg2: #74B9FF; }}

/* Section headers */
.section-title {{
    font-size: 20px;
    font-weight: 800;
    margin: 10px 0 12px 0;
    color: {THEME['text']};
}}

/* Badge */
.badge {{
    display: inline-block;
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 700;
}}
.badge-income {{ background: #DFF6EE; color: #00875A; }}
.badge-expense {{ background: #FFE3E0; color: #D63447; }}

.stButton>button {{
    border-radius: 10px;
    font-weight: 600;
}}

div[data-testid="stMetricValue"] {{ font-weight: 800; color: {THEME['text']}; }}
div[data-testid="stMetricLabel"] {{ color: {THEME['text_muted']}; }}

.sidebar-title {{
    font-size: 22px;
    font-weight: 800;
    background: linear-gradient(90deg, #6C5CE7, #00CEC9);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 0px;
}}

.lock-screen {{
    max-width: 360px;
    margin: 10vh auto 0 auto;
    text-align: center;
}}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

CURRENCY = db.get_setting("currency", "$")
BUSINESS_NAME = db.get_setting("business_name", "My Business")


def money(x):
    try:
        return f"{CURRENCY}{x:,.2f}"
    except Exception:
        return f"{CURRENCY}0.00"


def style_fig(fig):
    """Applies the current dark/light Plotly template with a transparent background
    so the app's own theme colors show through consistently."""
    fig.update_layout(
        template=PLOTLY_TEMPLATE,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color=THEME["text"],
    )
    return fig


# ----------------------------------------------------------------------------
# SIMPLE FAQ CHATBOT (rule-based keyword matching — no API key, works offline)
# ----------------------------------------------------------------------------
FAQ_DATA = [
    (["add", "new", "log", "record", "enter", "create transaction"],
     "Go to **➕ Add Transaction** in the sidebar, choose Income or Expense, pick a category, "
     "enter the amount and any details, then click **Save Transaction**."),

    (["edit", "update", "change", "fix", "correct", "modify"],
     "Open **📒 Transactions**, edit any cell directly in the table, then click **💾 Save Edits** "
     "to make it permanent."),

    (["delete", "remove", "undo"],
     "On the **📒 Transactions** page, pick the row ID(s) in the 'Delete by ID' box and click "
     "**🗑️ Delete Selected**. This can't be undone, so double-check the ID first."),

    (["budget", "limit", "overspend", "over budget"],
     "Go to **🎯 Budgets**, pick an expense category, set a monthly limit, and click **Set Budget**. "
     "A progress bar tracks spending and turns red if you go over."),

    (["export", "csv", "download", "backup", "excel"],
     "On the **📒 Transactions** page, apply any filters you want, then click "
     "**⬇️ Export Filtered to CSV** to download a spreadsheet-ready file."),

    (["currency", "symbol", "dollar", "rupee", "pkr", "$"],
     "Go to **⚙️ Settings** and update the Currency Symbol field, then click Save Settings. "
     "It updates everywhere in the app instantly."),

    (["category", "categories"],
     "New categories can be added right from the **➕ Add Transaction** page — choose "
     "'Add new category...' in the dropdown. You can also delete unused categories there."),

    (["private", "privacy", "safe", "secure", "cloud", "server", "data go", "stored"],
     "All your data stays on your own computer in a single local file called "
     "`expense_tracker.db`. Nothing is sent to the internet."),

    (["dashboard", "kpi", "chart", "graph", "mean", "show"],
     "The **📊 Dashboard** shows your total income, expenses, and balance for a date range you pick, "
     "plus charts for spending by category, trends over time, and payment methods."),

    (["search", "filter", "find"],
     "On the **📒 Transactions** page you can filter by type, category, and date range, or use the "
     "search box to find notes or customer/vendor names."),

    (["reset", "wipe", "clear all", "delete everything", "start over"],
     "Go to **⚙️ Settings**, scroll to the Danger Zone, type `DELETE ALL` to confirm, then click "
     "**🗑️ Wipe All Transaction Data**. This is permanent, so use it carefully."),

    (["report", "monthly", "trend", "heatmap", "leaderboard"],
     "The **📈 Reports** page has month-by-month comparisons, a running balance trend, a category "
     "spending heatmap, and a leaderboard of your top categories."),

    (["payment method", "cash", "bank", "wallet"],
     "You can choose a payment method (Cash, Bank Transfer, Card, Mobile Wallet, etc.) for every "
     "transaction, and see a breakdown of it on the Dashboard."),

    (["hi", "hello", "hey", "help", "what can you"],
     "Hi! I can help with things like adding transactions, setting budgets, exporting data, or "
     "finding your way around the app. What would you like to know?"),
]

FAQ_FALLBACK = (
    "I'm not sure about that one — I can only help with basic how-to questions about this app "
    "(adding transactions, budgets, exporting, categories, privacy, etc.). Try rephrasing, or "
    "check the page sidebar for the feature you're after."
)


def get_bot_response(text):
    t = text.lower()
    best_match, best_score = None, 0
    for keywords, answer in FAQ_DATA:
        score = sum(1 for kw in keywords if kw in t)
        if score > best_score:
            best_score, best_match = score, answer
    return best_match if best_match else FAQ_FALLBACK


# ----------------------------------------------------------------------------
# PIN LOCK GATE — shown before anything else if a PIN has been set
# ----------------------------------------------------------------------------
if "authenticated" not in st.session_state:
    st.session_state.authenticated = not db.has_pin()

if not st.session_state.authenticated:
    st.markdown('<div class="lock-screen">', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-title" style="font-size:28px;">💰 Expense Tracker</div>', unsafe_allow_html=True)
    st.write("")
    st.markdown("#### 🔒 Enter your PIN to unlock")
    pin_attempt = st.text_input("PIN", type="password", label_visibility="collapsed", placeholder="PIN")
    if st.button("Unlock", use_container_width=True):
        if db.verify_pin(pin_attempt):
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Incorrect PIN. Please try again.")
    st.markdown("</div>", unsafe_allow_html=True)
    st.stop()


# ----------------------------------------------------------------------------
# SIDEBAR NAVIGATION
# ----------------------------------------------------------------------------
with st.sidebar:
    st.markdown('<div class="sidebar-title">💰 Expense Tracker</div>', unsafe_allow_html=True)
    st.caption(BUSINESS_NAME)
    st.markdown("---")
    page = st.radio(
        "Navigate",
        ["📊 Dashboard", "➕ Add Transaction", "📒 Transactions", "🎯 Budgets", "📈 Reports", "💬 Help & FAQ", "⚙️ Settings"],
        label_visibility="collapsed",
    )
    st.markdown("---")
    df_all = db.get_transactions_df()
    if not df_all.empty:
        total_income = df_all.loc[df_all["type"] == "Income", "amount"].sum()
        total_expense = df_all.loc[df_all["type"] == "Expense", "amount"].sum()
        st.caption("Quick Snapshot")
        st.progress(min(1.0, total_expense / total_income) if total_income > 0 else 0)
        st.caption(f"Spent {money(total_expense)} of {money(total_income)} earned")
    st.markdown("---")

    new_dark = st.toggle("🌙 Dark Mode", value=DARK_MODE)
    if new_dark != DARK_MODE:
        db.set_setting("dark_mode", "true" if new_dark else "false")
        st.rerun()

    if db.has_pin():
        if st.button("🔒 Lock App", use_container_width=True):
            st.session_state.authenticated = False
            st.rerun()

    st.markdown("---")
    st.caption("Made with ❤️ using Streamlit")


# ----------------------------------------------------------------------------
# DASHBOARD
# ----------------------------------------------------------------------------
if page == "📊 Dashboard":
    st.markdown(f"### 👋 Welcome back — here's how **{BUSINESS_NAME}** is doing")

    df = db.get_transactions_df()

    # Date range filter
    colf1, colf2, colf3 = st.columns([1, 1, 2])
    with colf1:
        default_start = date.today().replace(day=1)
        start_date = st.date_input("From", value=default_start, key="dash_start")
    with colf2:
        end_date = st.date_input("To", value=date.today(), key="dash_end")

    if not df.empty:
        mask = (df["date"].dt.date >= start_date) & (df["date"].dt.date <= end_date)
        dff = df.loc[mask]
    else:
        dff = df

    income = dff.loc[dff["type"] == "Income", "amount"].sum() if not dff.empty else 0
    expense = dff.loc[dff["type"] == "Expense", "amount"].sum() if not dff.empty else 0
    balance = income - expense
    count = len(dff)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"""<div class="kpi-card kpi-income"><div class="icon">💵</div>
            <div class="label">TOTAL INCOME</div><div class="value">{money(income)}</div>
            <div class="sub">In selected period</div></div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""<div class="kpi-card kpi-expense"><div class="icon">💸</div>
            <div class="label">TOTAL EXPENSES</div><div class="value">{money(expense)}</div>
            <div class="sub">In selected period</div></div>""", unsafe_allow_html=True)
    with c3:
        st.markdown(f"""<div class="kpi-card kpi-balance"><div class="icon">🏦</div>
            <div class="label">NET BALANCE</div><div class="value">{money(balance)}</div>
            <div class="sub">{'Surplus' if balance>=0 else 'Deficit'}</div></div>""", unsafe_allow_html=True)
    with c4:
        st.markdown(f"""<div class="kpi-card kpi-count"><div class="icon">🧾</div>
            <div class="label">TRANSACTIONS</div><div class="value">{count}</div>
            <div class="sub">Records logged</div></div>""", unsafe_allow_html=True)

    st.write("")
    st.markdown("---")

    if dff.empty:
        st.info("No transactions yet in this period. Head to **➕ Add Transaction** to get started!")
    else:
        colA, colB = st.columns([1, 1])

        with colA:
            st.markdown('<div class="section-title">🥧 Expenses by Category</div>', unsafe_allow_html=True)
            exp_by_cat = dff[dff["type"] == "Expense"].groupby("category")["amount"].sum().reset_index()
            if not exp_by_cat.empty:
                fig = px.pie(
                    exp_by_cat, names="category", values="amount", hole=0.55,
                    color_discrete_sequence=px.colors.qualitative.Set3,
                )
                fig.update_traces(textposition="inside", textinfo="percent+label")
                fig.update_layout(margin=dict(t=10, b=10, l=10, r=10), showlegend=True, height=360)
                st.plotly_chart(style_fig(fig), use_container_width=True)
            else:
                st.caption("No expenses recorded in this period.")

        with colB:
            st.markdown('<div class="section-title">📈 Income vs Expense Trend</div>', unsafe_allow_html=True)
            trend = dff.copy()
            trend["day"] = trend["date"].dt.date
            trend_g = trend.groupby(["day", "type"])["amount"].sum().reset_index()
            fig2 = px.area(
                trend_g, x="day", y="amount", color="type",
                color_discrete_map={"Income": "#00B894", "Expense": "#FF6B6B"},
            )
            fig2.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=360, legend_title_text="")
            st.plotly_chart(style_fig(fig2), use_container_width=True)

        colC, colD = st.columns([1, 1])
        with colC:
            st.markdown('<div class="section-title">🏆 Top Expense Categories</div>', unsafe_allow_html=True)
            top_cats = dff[dff["type"] == "Expense"].groupby("category")["amount"].sum().sort_values(ascending=True).reset_index()
            if not top_cats.empty:
                fig3 = px.bar(
                    top_cats.tail(8), x="amount", y="category", orientation="h",
                    color="amount", color_continuous_scale="Sunsetdark", text="amount"
                )
                fig3.update_traces(texttemplate=f"{CURRENCY}%{{text:,.0f}}", textposition="outside")
                fig3.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=340, coloraxis_showscale=False,
                                    xaxis_title="", yaxis_title="")
                st.plotly_chart(style_fig(fig3), use_container_width=True)
            else:
                st.caption("No expenses recorded in this period.")

        with colD:
            st.markdown('<div class="section-title">💳 Payment Method Split</div>', unsafe_allow_html=True)
            pm = dff.groupby("payment_method")["amount"].sum().reset_index()
            if not pm.empty:
                fig4 = px.bar(
                    pm, x="payment_method", y="amount", color="payment_method",
                    color_discrete_sequence=px.colors.qualitative.Pastel,
                    text="amount"
                )
                fig4.update_traces(texttemplate=f"{CURRENCY}%{{text:,.0f}}", textposition="outside")
                fig4.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=340, showlegend=False,
                                    xaxis_title="", yaxis_title="")
                st.plotly_chart(style_fig(fig4), use_container_width=True)

        st.markdown("---")
        st.markdown('<div class="section-title">🕐 Recent Transactions</div>', unsafe_allow_html=True)
        recent = dff.sort_values("date", ascending=False).head(8).copy()
        recent["date"] = recent["date"].dt.strftime("%d %b %Y")
        recent["amount"] = recent.apply(lambda r: f"{'+' if r['type']=='Income' else '-'}{money(r['amount'])}", axis=1)
        st.dataframe(
            recent[["date", "type", "category", "amount", "payment_method", "party", "description"]],
            use_container_width=True, hide_index=True,
        )


# ----------------------------------------------------------------------------
# ADD TRANSACTION
# ----------------------------------------------------------------------------
elif page == "➕ Add Transaction":
    st.markdown("### ➕ Log a New Transaction")
    st.caption("Add income (sales, salary...) or expenses (stock, rent, bills...) in a few seconds.")

    ttype = st.radio("Transaction Type", ["Expense", "Income"], horizontal=True)
    cats = db.get_categories(ttype)
    cat_labels = [f"{c['icon']} {c['name']}" for c in cats] + ["➕ Add new category..."]

    with st.form("add_txn_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            tdate = st.date_input("Date", value=date.today())
            cat_choice = st.selectbox("Category", cat_labels)
            amount = st.number_input("Amount", min_value=0.0, step=1.0, format="%.2f")
        with col2:
            payment_method = st.selectbox("Payment Method", db.PAYMENT_METHODS)
            party = st.text_input("Customer / Vendor (optional)", placeholder="e.g. Ali Traders")
            description = st.text_input("Note (optional)", placeholder="e.g. Weekly grocery restock")

        new_cat_name = None
        if cat_choice == "➕ Add new category...":
            new_cat_name = st.text_input("New category name")

        submitted = st.form_submit_button("💾 Save Transaction", use_container_width=True)

        if submitted:
            if amount <= 0:
                st.error("Amount must be greater than 0.")
            else:
                category = cat_choice.split(" ", 1)[1] if cat_choice != "➕ Add new category..." else new_cat_name
                if cat_choice == "➕ Add new category...":
                    if not new_cat_name:
                        st.error("Please enter a name for the new category.")
                        st.stop()
                    db.add_category(new_cat_name, ttype)
                    category = new_cat_name
                db.add_transaction(
                    str(tdate), ttype, category, amount, payment_method, party, description
                )
                st.success(f"✅ {ttype} of {money(amount)} saved under '{category}'.")
                st.balloons()

    st.markdown("---")
    st.markdown("#### Manage Categories")
    ic1, ic2 = st.columns(2)
    with ic1:
        st.caption("Expense categories")
        for c in db.get_categories("Expense"):
            cc1, cc2 = st.columns([4, 1])
            cc1.write(f"{c['icon']} {c['name']}")
            if cc2.button("🗑️", key=f"delcat_exp_{c['id']}"):
                db.delete_category(c["name"])
                st.rerun()
    with ic2:
        st.caption("Income categories")
        for c in db.get_categories("Income"):
            cc1, cc2 = st.columns([4, 1])
            cc1.write(f"{c['icon']} {c['name']}")
            if cc2.button("🗑️", key=f"delcat_inc_{c['id']}"):
                db.delete_category(c["name"])
                st.rerun()


# ----------------------------------------------------------------------------
# TRANSACTIONS (table, filter, edit, delete, export)
# ----------------------------------------------------------------------------
elif page == "📒 Transactions":
    st.markdown("### 📒 All Transactions")

    df = db.get_transactions_df()

    if df.empty:
        st.info("No transactions recorded yet.")
    else:
        f1, f2, f3, f4 = st.columns([1, 1, 1, 2])
        with f1:
            type_filter = st.multiselect("Type", ["Income", "Expense"], default=["Income", "Expense"])
        with f2:
            all_cats = sorted(df["category"].unique().tolist())
            cat_filter = st.multiselect("Category", all_cats, default=[])
        with f3:
            date_range = st.date_input("Date range", value=(df["date"].min().date(), df["date"].max().date()))
        with f4:
            search = st.text_input("🔍 Search notes / party", placeholder="Search...")

        dff = df.copy()
        if type_filter:
            dff = dff[dff["type"].isin(type_filter)]
        if cat_filter:
            dff = dff[dff["category"].isin(cat_filter)]
        if isinstance(date_range, tuple) and len(date_range) == 2:
            dff = dff[(dff["date"].dt.date >= date_range[0]) & (dff["date"].dt.date <= date_range[1])]
        if search:
            s = search.lower()
            dff = dff[
                dff["description"].fillna("").str.lower().str.contains(s)
                | dff["party"].fillna("").str.lower().str.contains(s)
            ]

        st.caption(f"Showing {len(dff)} of {len(df)} transactions")

        display_df = dff.copy()
        display_df["date"] = display_df["date"].dt.strftime("%Y-%m-%d")
        display_df = display_df[["id", "date", "type", "category", "amount", "payment_method", "party", "description"]]

        edited = st.data_editor(
            display_df,
            use_container_width=True,
            hide_index=True,
            num_rows="fixed",
            column_config={
                "id": st.column_config.NumberColumn("ID", disabled=True),
                "amount": st.column_config.NumberColumn("Amount", format=f"{CURRENCY}%.2f"),
                "type": st.column_config.SelectboxColumn("Type", options=["Income", "Expense"]),
            },
            key="txn_editor",
        )

        colb1, colb2, colb3 = st.columns([1, 1, 3])
        with colb1:
            if st.button("💾 Save Edits", use_container_width=True):
                for _, row in edited.iterrows():
                    db.update_transaction(
                        int(row["id"]), row["date"], row["type"], row["category"],
                        float(row["amount"]), row["payment_method"], row["party"], row["description"]
                    )
                st.success("Changes saved.")
                st.rerun()
        with colb2:
            ids_to_delete = st.multiselect("Delete by ID", dff["id"].tolist())
            if st.button("🗑️ Delete Selected", use_container_width=True) and ids_to_delete:
                db.delete_transactions(ids_to_delete)
                st.success(f"Deleted {len(ids_to_delete)} record(s).")
                st.rerun()
        with colb3:
            csv_buf = io.StringIO()
            dff.to_csv(csv_buf, index=False)
            st.download_button(
                "⬇️ Export Filtered to CSV", data=csv_buf.getvalue(),
                file_name=f"transactions_{date.today()}.csv", mime="text/csv",
                use_container_width=True,
            )


# ----------------------------------------------------------------------------
# BUDGETS
# ----------------------------------------------------------------------------
elif page == "🎯 Budgets":
    st.markdown("### 🎯 Monthly Budgets")
    st.caption("Set spending limits per category and track progress for the current month.")

    exp_cats = [c["name"] for c in db.get_categories("Expense")]
    with st.form("budget_form"):
        bc1, bc2, bc3 = st.columns([2, 2, 1])
        with bc1:
            b_cat = st.selectbox("Category", exp_cats)
        with bc2:
            b_limit = st.number_input("Monthly Limit", min_value=0.0, step=10.0, format="%.2f")
        with bc3:
            st.write("")
            st.write("")
            b_submit = st.form_submit_button("Set Budget", use_container_width=True)
        if b_submit and b_limit > 0:
            db.set_budget(b_cat, b_limit)
            st.success(f"Budget set for {b_cat}: {money(b_limit)}/month")
            st.rerun()

    st.markdown("---")
    budgets = db.get_budgets()
    if not budgets:
        st.info("No budgets set yet. Add one above to start tracking.")
    else:
        df = db.get_transactions_df()
        this_month = date.today().replace(day=1)
        if not df.empty:
            month_df = df[(df["type"] == "Expense") & (df["date"].dt.date >= this_month)]
        else:
            month_df = pd.DataFrame(columns=["category", "amount"])

        for b in budgets:
            spent = month_df.loc[month_df["category"] == b["category"], "amount"].sum() if not month_df.empty else 0
            limit = b["monthly_limit"]
            pct = min(spent / limit, 1.0) if limit > 0 else 0
            over = spent > limit

            col1, col2, col3 = st.columns([3, 1, 0.6])
            with col1:
                st.markdown(f"**{b['category']}** — {money(spent)} of {money(limit)}")
                st.progress(pct, text=f"{pct*100:.0f}%")
                if over:
                    st.error(f"⚠️ Over budget by {money(spent - limit)}!")
            with col2:
                st.metric("Remaining", money(max(limit - spent, 0)))
            with col3:
                st.write("")
                st.write("")
                if st.button("🗑️", key=f"delbudget_{b['category']}"):
                    db.delete_budget(b["category"])
                    st.rerun()
            st.markdown("---")


# ----------------------------------------------------------------------------
# REPORTS
# ----------------------------------------------------------------------------
elif page == "📈 Reports":
    st.markdown("### 📈 Reports & Analytics")

    df = db.get_transactions_df()
    if df.empty:
        st.info("Add some transactions to see reports here.")
    else:
        df["month"] = df["date"].dt.to_period("M").astype(str)

        st.markdown('<div class="section-title">📊 Monthly Income vs Expense</div>', unsafe_allow_html=True)
        monthly = df.groupby(["month", "type"])["amount"].sum().reset_index()
        fig = px.bar(
            monthly, x="month", y="amount", color="type", barmode="group",
            color_discrete_map={"Income": "#00B894", "Expense": "#FF6B6B"},
        )
        fig.update_layout(height=380, legend_title_text="", xaxis_title="", yaxis_title="Amount")
        st.plotly_chart(style_fig(fig), use_container_width=True)

        col1, col2 = st.columns(2)
        with col1:
            st.markdown('<div class="section-title">📉 Net Balance Over Time</div>', unsafe_allow_html=True)
            monthly_net = df.copy()
            monthly_net["signed"] = monthly_net.apply(lambda r: r["amount"] if r["type"] == "Income" else -r["amount"], axis=1)
            net_by_month = monthly_net.groupby("month")["signed"].sum().cumsum().reset_index()
            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(
                x=net_by_month["month"], y=net_by_month["signed"],
                mode="lines+markers", fill="tozeroy",
                line=dict(color="#6C5CE7", width=3),
            ))
            fig2.update_layout(height=340, xaxis_title="", yaxis_title="Cumulative Balance")
            st.plotly_chart(style_fig(fig2), use_container_width=True)

        with col2:
            st.markdown('<div class="section-title">🔥 Category Trend Heatmap</div>', unsafe_allow_html=True)
            exp = df[df["type"] == "Expense"]
            if not exp.empty:
                pivot = exp.pivot_table(index="category", columns="month", values="amount", aggfunc="sum", fill_value=0)
                fig3 = px.imshow(
                    pivot, color_continuous_scale="Purples", aspect="auto",
                    labels=dict(color="Amount")
                )
                fig3.update_layout(height=340)
                st.plotly_chart(style_fig(fig3), use_container_width=True)
            else:
                st.caption("No expense data yet.")

        st.markdown('<div class="section-title">🏅 Category Leaderboard (All Time)</div>', unsafe_allow_html=True)
        leader = df.groupby(["type", "category"])["amount"].sum().reset_index().sort_values("amount", ascending=False)
        leader["amount"] = leader["amount"].apply(money)
        st.dataframe(leader, use_container_width=True, hide_index=True)

        # Summary stats
        st.markdown("---")
        s1, s2, s3, s4 = st.columns(4)
        avg_daily_exp = df[df["type"] == "Expense"].groupby(df["date"].dt.date)["amount"].sum().mean()
        biggest_txn = df.loc[df["amount"].idxmax()]
        most_common_cat = df["category"].mode().iloc[0] if not df.empty else "-"
        s1.metric("Avg Daily Expense", money(avg_daily_exp if pd.notna(avg_daily_exp) else 0))
        s2.metric("Biggest Transaction", money(biggest_txn["amount"]))
        s3.metric("Most Frequent Category", most_common_cat)
        s4.metric("Total Records", len(df))


# ----------------------------------------------------------------------------
# HELP & FAQ CHATBOT
# ----------------------------------------------------------------------------
elif page == "💬 Help & FAQ":
    st.markdown("### 💬 Help & FAQ")
    st.caption("Ask a quick question about using the app — this runs locally, no internet needed.")

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = [
            {"role": "assistant", "content": "Hi! Ask me how to do something in the app, "
                                              "or tap a quick question below to get started."}
        ]

    quick_qs = ["How do I add a transaction?", "How do I set a budget?", "How do I export my data?", "Is my data private?"]
    qcols = st.columns(len(quick_qs))
    picked = None
    for c, q in zip(qcols, quick_qs):
        if c.button(q, use_container_width=True):
            picked = q

    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    typed = st.chat_input("Type your question...")
    user_msg = picked or typed

    if user_msg:
        st.session_state.chat_history.append({"role": "user", "content": user_msg})
        reply = get_bot_response(user_msg)
        st.session_state.chat_history.append({"role": "assistant", "content": reply})
        st.rerun()

    st.markdown("---")
    if st.button("🧹 Clear Chat"):
        st.session_state.chat_history = []
        st.rerun()


# ----------------------------------------------------------------------------
# SETTINGS
# ----------------------------------------------------------------------------
elif page == "⚙️ Settings":
    st.markdown("### ⚙️ Settings")

    with st.form("settings_form"):
        biz_name = st.text_input("Business / Profile Name", value=BUSINESS_NAME)
        currency = st.text_input("Currency Symbol", value=CURRENCY, max_chars=5)
        saved = st.form_submit_button("💾 Save Settings")
        if saved:
            db.set_setting("business_name", biz_name)
            db.set_setting("currency", currency)
            st.success("Settings saved! Refresh to see changes everywhere.")
            st.rerun()

    st.markdown("---")
    st.markdown("#### 🔒 App Lock")
    if not db.has_pin():
        st.caption("Add a PIN to require it before the app opens — handy for a shared shop tablet or computer.")
        with st.form("set_pin_form"):
            new_pin = st.text_input("New PIN (4+ characters)", type="password")
            confirm_pin = st.text_input("Confirm PIN", type="password")
            enable = st.form_submit_button("Enable PIN Lock")
            if enable:
                if len(new_pin) < 4:
                    st.error("PIN must be at least 4 characters.")
                elif new_pin != confirm_pin:
                    st.error("PINs don't match.")
                else:
                    db.set_pin(new_pin)
                    st.success("PIN lock enabled. You'll need it next time you open the app.")
                    st.rerun()
    else:
        st.success("PIN lock is currently **enabled**.")
        with st.expander("Change PIN"):
            with st.form("change_pin_form"):
                cur_pin = st.text_input("Current PIN", type="password")
                new_pin2 = st.text_input("New PIN (4+ characters)", type="password")
                confirm_pin2 = st.text_input("Confirm New PIN", type="password")
                change = st.form_submit_button("Update PIN")
                if change:
                    if not db.verify_pin(cur_pin):
                        st.error("Current PIN is incorrect.")
                    elif len(new_pin2) < 4:
                        st.error("New PIN must be at least 4 characters.")
                    elif new_pin2 != confirm_pin2:
                        st.error("New PINs don't match.")
                    else:
                        db.set_pin(new_pin2)
                        st.success("PIN updated.")
        with st.expander("Remove PIN Lock"):
            with st.form("remove_pin_form"):
                cur_pin2 = st.text_input("Current PIN", type="password", key="remove_pin_input")
                remove = st.form_submit_button("Disable PIN Lock")
                if remove:
                    if db.verify_pin(cur_pin2):
                        db.remove_pin()
                        st.success("PIN lock removed.")
                        st.rerun()
                    else:
                        st.error("Current PIN is incorrect.")

    st.markdown("---")
    st.markdown("#### 💾 Backup & Restore")
    st.caption("Your whole app — transactions, categories, budgets, and settings — lives in one file. Back it up anytime, or move it to a new computer.")

    bcol1, bcol2 = st.columns(2)
    with bcol1:
        st.markdown("**Download a backup**")
        backup_bytes = db.export_db_bytes()
        st.download_button(
            "⬇️ Download Backup",
            data=backup_bytes,
            file_name=f"expense_tracker_backup_{date.today()}.db",
            mime="application/octet-stream",
            use_container_width=True,
        )
    with bcol2:
        st.markdown("**Restore from a backup**")
        uploaded = st.file_uploader("Choose a .db backup file", type=["db"], label_visibility="collapsed")
        if uploaded is not None:
            st.warning("Restoring will replace all current data with the contents of this file. Your existing data will be saved as a `.bak` file first.")
            if st.button("♻️ Restore This Backup", use_container_width=True):
                success, message = db.import_db_bytes(uploaded.getvalue())
                if success:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)

    st.markdown("---")
    st.markdown("#### Danger Zone")
    st.warning("This will permanently delete ALL transactions. This cannot be undone.")
    confirm = st.text_input("Type DELETE ALL to confirm")
    if st.button("🗑️ Wipe All Transaction Data"):
        if confirm == "DELETE ALL":
            df = db.get_transactions_df()
            if not df.empty:
                db.delete_transactions(df["id"].tolist())
            st.success("All transactions deleted.")
            st.rerun()
        else:
            st.error("Type the confirmation phrase exactly to proceed.")

    st.markdown("---")
    st.markdown("#### About")
    st.caption(
        "Expense Tracker v1.0 — built with Streamlit, Plotly & SQLite. "
        "All your data is stored locally in `expense_tracker.db`, right next to this app. "
        "Nothing is sent anywhere."
    )



# python -m streamlit run app.py