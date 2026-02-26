
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import re
import io
from datetime import datetime, date

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Heritage Shops — Inventory & Forecast",
    page_icon="🏪",
    layout="wide",
    initial_sidebar_state="expanded",
)

CURRENT_YEAR = datetime.now().year
CURRENT_MONTH = datetime.now().month

# ── Seasonal index for NL tourism (Jan=1 … Dec=12) ───────────────────────────
SEASONAL_INDEX = {1:0.35, 2:0.35, 3:0.40, 4:0.55, 5:0.75, 6:1.20,
                  7:2.50, 8:2.40, 9:1.50, 10:0.90, 11:0.55, 12:0.80}

# ── Hard exclusion rules ─────────────────────────────────────────────────────
EXCLUDE_KEYWORDS = ["shipping charges", "environmental charge", "gift card",
                    "gift certificate", "poster tube", "st-receive",
                    "clearance", "discontinued", "out of print"]

DATED_KEYWORDS   = ["calendar", "planner", "diary", "agenda", "almanac"]

def parse_csv(uploaded_file):
    """Parse the Heritage POS CSV format (header metadata + data rows)."""
    content = uploaded_file.read().decode("utf-8", errors="replace")
    lines   = content.splitlines()

    # Extract branch from header
    branch = "Unknown"
    date_from, date_to = "", ""
    for line in lines[:15]:
        if "Branch" in line:
            m = re.search(r"Branch\s+(\d+)", line)
            if m:
                branch = m.group(1)
        if "Date Range From" in line:
            m = re.search(r"From\s+(\S+)\s+To\s+(\S+)", line)
            if m:
                date_from, date_to = m.group(1), m.group(2)

    # Find header row
    header_idx = None
    for i, line in enumerate(lines):
        if "Item Number" in line and "Description" in line:
            header_idx = i
            break
    if header_idx is None:
        return None, branch, date_from, date_to

    # Build clean header
    raw_header = lines[header_idx]
    cols = ["Item Number","Department","Brand","Supplier",
            "Description Code","Description","Supplier Category",
            "Number","Number Sold","Selling","Cost","Profit","Margin"]

    data_rows = []
    for line in lines[header_idx+1:]:
        line = line.strip()
        if not line or line.startswith("-") or "Item Number" in line:
            continue
        # regex parse
        m = re.match(
            r"^(\d{4,7})"          # Item Number
            r"(\d{3})"             # Department
            r"(\S+?)"              # Brand
            r"(\S+?)"              # Supplier
            r"(.+?)\s+"            # Description Code + Description (greedy)
            r"(\d+)\s+"           # Number Sold
            r"([\d,]+\.\d{2})\s+"  # Selling
            r"([\d,]+\.\d{2})\s+"  # Cost
            r"(-?[\d,]+\.\d{2})\s+" # Profit
            r"(-?[\d,.]+)$",       # Margin
            line
        )
        if m:
            g = m.groups()
            data_rows.append({
                "Item Number":  g[0],
                "Department":   g[1],
                "Brand":        g[2],
                "Supplier":     g[3],
                "Description":  g[4].strip(),
                "Number Sold":  int(g[5].replace(",", "")),
                "Selling":      float(g[6].replace(",", "")),
                "Cost":         float(g[7].replace(",", "")),
                "Profit":       float(g[8].replace(",", "")),
                "Margin":       float(g[9].replace(",", "").replace("%", "")),
            })

    if not data_rows:
        return None, branch, date_from, date_to

    df = pd.DataFrame(data_rows)
    df["Branch"] = branch
    return df, branch, date_from, date_to


def classify_velocity(sold):
    if sold >= 50:   return "🔥 Fast"
    if sold >= 10:   return "⚡ Medium"
    if sold >= 1:    return "🐢 Slow"
    return "💀 Dead"


def get_exclusion_reason(desc, item_num, margin, sold,
                         custom_exclude_keywords, custom_exclude_items):
    desc_lower = desc.lower()

    if str(item_num) in custom_exclude_items:
        return "Manually excluded"

    for kw in custom_exclude_keywords + EXCLUDE_KEYWORDS:
        if kw.lower() in desc_lower:
            return f"Service/excluded keyword: '{kw}'"

    for kw in DATED_KEYWORDS:
        if kw in desc_lower:
            year_match = re.search(r"\b(20\d{2})\b", desc)
            if year_match:
                item_year = int(year_match.group(1))
                if item_year < CURRENT_YEAR:
                    return f"Dated item ({item_year} < {CURRENT_YEAR})"
                elif item_year == CURRENT_YEAR and CURRENT_MONTH > 3:
                    return f"Calendar year {item_year} — season passed (Mar cutoff)"

    if margin < 0:
        return f"Negative margin ({margin:.1f}%)"

    if sold == 0:
        return "Zero sales — potential dead stock"

    return None   # no exclusion


def build_reorder(df, cruise_df, reorder_weeks, safety_stock_pct,
                  custom_exclude_keywords, custom_exclude_items):
    """Generate smart reorder list with forecasting."""
    next_month = (CURRENT_MONTH % 12) + 1
    seasonal   = SEASONAL_INDEX.get(next_month, 1.0)

    # Cruise multiplier: if cruise data uploaded, count ships next month
    cruise_mult = 1.0
    if cruise_df is not None and not cruise_df.empty:
        nm = f"{CURRENT_YEAR}-{next_month:02d}"
        next_mo_cruises = cruise_df[cruise_df["Month"] == nm]
        total_pax = next_mo_cruises["Passengers"].sum() if "Passengers" in next_mo_cruises.columns else 0
        if total_pax > 5000:
            cruise_mult = 1.35
        elif total_pax > 2000:
            cruise_mult = 1.20
        elif total_pax > 0:
            cruise_mult = 1.10

    rows = []
    for _, r in df.iterrows():
        reason = get_exclusion_reason(
            r["Description"], r["Item Number"], r["Margin"],
            r["Number Sold"], custom_exclude_keywords, custom_exclude_items)

        sold       = r["Number Sold"]
        avg_weekly = sold / 52.0
        forecast   = avg_weekly * reorder_weeks * seasonal * cruise_mult
        safety     = forecast * (safety_stock_pct / 100)
        suggested  = max(1, round(forecast + safety))

        velocity   = classify_velocity(sold)

        if reason:
            priority = "❌ EXCLUDED"
        elif suggested >= 20:
            priority = "🚨 URGENT"
        elif suggested >= 10:
            priority = "⚠️ WARNING"
        else:
            priority = "✅ OK"

        rows.append({
            "Priority":       priority,
            "Item #":         r["Item Number"],
            "Description":    r["Description"],
            "Brand":          r.get("Brand", ""),
            "Dept":           r.get("Department", ""),
            "Velocity":       velocity,
            "Total Sold":     sold,
            "Avg/Week":       round(avg_weekly, 1),
            "Seasonal Idx":   seasonal,
            "Cruise Mult":    round(cruise_mult, 2),
            "Forecast Qty":   round(forecast, 1),
            "Suggested Order":suggested,
            "Margin %":       r["Margin"],
            "Exclusion Reason": reason or "",
            "Branch":         r.get("Branch", ""),
        })

    return pd.DataFrame(rows)


# ══════════════════════════════════════════════════════════════════════════════
# QA AGENT CHAT
# ══════════════════════════════════════════════════════════════════════════════
def agent_respond(user_msg, reorder_df, custom_exclude_keywords,
                  custom_exclude_items, context_df):
    msg   = user_msg.lower().strip()
    reply = ""

    # ── why is X excluded / in the list ──────────────────────────────────────
    for keyword in ["why is", "why was", "explain"]:
        if keyword in msg:
            # Try to find item by description fragment or item number
            token = msg.split(keyword)[-1].strip().strip("?").strip()
            matches = reorder_df[
                reorder_df["Description"].str.lower().str.contains(token, na=False) |
                reorder_df["Item #"].astype(str).str.contains(token, na=False)
            ]
            if not matches.empty:
                row = matches.iloc[0]
                excl = row["Exclusion Reason"]
                if excl:
                    reply = (f"**{row['Description']}** (Item #{row['Item #']}) "
                             f"is **excluded** because: _{excl}_\n\n"
                             f"It has been removed from the reorder suggestions automatically.")
                else:
                    reply = (f"**{row['Description']}** (Item #{row['Item #']}) "
                             f"is recommended with priority **{row['Priority']}**.\n\n"
                             f"- Total Sold: {row['Total Sold']}\n"
                             f"- Velocity: {row['Velocity']}\n"
                             f"- Seasonal Index: {row['Seasonal Idx']}\n"
                             f"- Cruise Multiplier: {row['Cruise Mult']}x\n"
                             f"- Suggested Order: **{row['Suggested Order']} units**")
            else:
                reply = f"I couldn't find an item matching **'{token}'** in the current reorder list."
            return reply, custom_exclude_keywords, custom_exclude_items

    # ── add exclusion rule ────────────────────────────────────────────────────
    if any(x in msg for x in ["exclude", "block", "remove", "never suggest"]):
        # Extract keyword in quotes or after the verb
        kw_match = re.search(r"[\"'](.*?)["\']", msg)
        if kw_match:
            new_kw = kw_match.group(1).lower()
            if new_kw not in custom_exclude_keywords:
                custom_exclude_keywords.append(new_kw)
            reply = (f"✅ Rule added: items containing **'{new_kw}'** will now be "
                     f"automatically excluded from reorder suggestions. "
                     f"Refresh the Reorder page to see the updated list.")
        else:
            reply = ("To add an exclusion rule, use quotes around the keyword.\n"
                     "Example: `exclude '2024 calendar'`")
        return reply, custom_exclude_keywords, custom_exclude_items

    # ── show URGENT items ─────────────────────────────────────────────────────
    if "urgent" in msg or "critical" in msg:
        urgent = reorder_df[reorder_df["Priority"] == "🚨 URGENT"]
        if urgent.empty:
            reply = "No URGENT items found with current settings."
        else:
            items = urgent[["Item #","Description","Suggested Order"]].head(10)
            reply = f"**🚨 URGENT items ({len(urgent)} total):**\n\n" + items.to_markdown(index=False)
        return reply, custom_exclude_keywords, custom_exclude_items

    # ── top sellers ───────────────────────────────────────────────────────────
    if any(x in msg for x in ["top", "best seller", "best selling", "highest"]):
        if context_df is not None:
            top = context_df.nlargest(10, "Number Sold")[["Item Number","Description","Number Sold","Margin"]]
            reply = "**🏆 Top 10 Best Sellers (by units sold):**\n\n" + top.to_markdown(index=False)
        else:
            reply = "No sales data loaded yet."
        return reply, custom_exclude_keywords, custom_exclude_items

    # ── cruise week ───────────────────────────────────────────────────────────
    if "cruise" in msg:
        souvenir_kwds = ["magnet", "postcard", "keychain", "ornament", "bookmark",
                         "lapel", "sticker", "soapstone"]
        if context_df is not None:
            mask = context_df["Description"].str.lower().apply(
                lambda d: any(kw in d for kw in souvenir_kwds))
            cruise_items = context_df[mask].nlargest(15, "Number Sold")[
                ["Item Number","Description","Number Sold"]]
            reply = ("**🚢 Recommended items for cruise week** (high-turnover souvenirs):\n\n"
                     + cruise_items.to_markdown(index=False))
        else:
            reply = "No sales data loaded. Upload a Sales History file first."
        return reply, custom_exclude_keywords, custom_exclude_items

    # ── exclusion list ────────────────────────────────────────────────────────
    if "exclusion" in msg or "rules" in msg or "list rule" in msg:
        all_rules = EXCLUDE_KEYWORDS + custom_exclude_keywords
        reply = ("**Current exclusion rules:**\n\n"
                 + "\n".join(f"- `{r}`" for r in all_rules))
        return reply, custom_exclude_keywords, custom_exclude_items

    # ── default ───────────────────────────────────────────────────────────────
    reply = (
        "Hi! I'm the Reorder QA Agent. I can help you with:\n\n"
        "- **Why is [item] excluded?** — Explains exclusion reason\n"
        "- **Why is [item] in the list?** — Shows forecast reasoning\n"
        "- **Show urgent items** — Lists all 🚨 URGENT reorders\n"
        "- **Top sellers** — Shows best-selling items\n"
        "- **What to order for cruise week** — Souvenir recommendations\n"
        "- **Exclude 'keyword'** — Adds a new exclusion rule\n"
        "- **Show exclusion rules** — Lists all active rules\n"
    )
    return reply, custom_exclude_keywords, custom_exclude_items


# ══════════════════════════════════════════════════════════════════════════════
# SESSION STATE INIT
# ══════════════════════════════════════════════════════════════════════════════
for key, default in {
    "sales_dfs":               {},    # branch → DataFrame
    "cruise_df":               None,
    "inventory_df":            None,
    "custom_exclude_keywords": [],
    "custom_exclude_items":    [],
    "chat_history":            [],
    "reorder_df":              None,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default


# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.image("https://via.placeholder.com/200x60?text=Heritage+Shops", width=200)
    st.markdown("---")

    role = st.selectbox("👤 Role", ["Warehouse Manager", "Store Supervisor", "Web Store"])

    if role == "Store Supervisor":
        branches_loaded = list(st.session_state.sales_dfs.keys())
        selected_branch = st.selectbox("🏪 Branch", branches_loaded if branches_loaded else ["(upload data first)"])
    else:
        selected_branch = "ALL"

    st.markdown("---")
    page = st.radio("📋 Navigation", [
        "📤 Data Hub",
        "📊 Dashboard",
        "🔮 Forecast & Reorder",
        "🤖 QA Agent Chat",
        "📈 Analytics",
        "⚙️ Settings",
    ])

    st.markdown("---")
    st.caption(f"📅 Today: {date.today().strftime('%b %d, %Y')}")
    st.caption(f"🗓 Season index next month: **{SEASONAL_INDEX.get((CURRENT_MONTH%12)+1, 1.0)}x**")


# ══════════════════════════════════════════════════════════════════════════════
# HELPER: get combined DF
# ══════════════════════════════════════════════════════════════════════════════
def get_active_df():
    if not st.session_state.sales_dfs:
        return None
    if selected_branch == "ALL":
        return pd.concat(st.session_state.sales_dfs.values(), ignore_index=True)
    return st.session_state.sales_dfs.get(selected_branch, None)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: DATA HUB
# ══════════════════════════════════════════════════════════════════════════════
if page == "📤 Data Hub":
    st.title("📤 Data Hub")
    st.markdown("Upload your data files here. All modules are optional except **Sales History**.")

    tab1, tab2, tab3, tab4 = st.tabs(["📦 Sales History", "🚢 Cruise Schedule", "🌤 Weather", "📋 Current Inventory"])

    with tab1:
        st.subheader("Sales History CSV")
        st.info("Upload one or more Sales History files (one per branch or combined). The app auto-detects branch numbers.")
        uploaded = st.file_uploader("Upload Sales History CSV(s)", type=["csv"],
                                    accept_multiple_files=True, key="sales_upload")
        if uploaded:
            for f in uploaded:
                df, branch, dfrom, dto = parse_csv(f)
                if df is not None and not df.empty:
                    st.session_state.sales_dfs[branch] = df
                    st.success(f"✅ Branch {branch} loaded — {len(df):,} items | {dfrom} → {dto}")
                else:
                    st.warning(f"⚠️ Could not parse {f.name}. Check format.")

        if st.session_state.sales_dfs:
            st.markdown("**Loaded branches:**")
            for b, d in st.session_state.sales_dfs.items():
                st.markdown(f"- Branch **{b}**: {len(d):,} items, "
                            f"{d['Number Sold'].sum():,} units sold, "
                            f"${d['Selling'].sum():,.0f} revenue")

    with tab2:
        st.subheader("🚢 Cruise Ship Schedule")
        st.info("Upload a CSV with columns: `Date` (YYYY-MM-DD), `Ship Name`, `Passengers`")
        sample_cruise = pd.DataFrame({
            "Date": ["2026-06-15","2026-06-22","2026-07-04","2026-07-11","2026-08-03"],
            "Ship Name": ["Norwegian Joy","Carnival Breeze","MSC Bellissima","Royal Caribbean","Celebrity Edge"],
            "Passengers": [4200, 3800, 5100, 4700, 3200]
        })
        st.dataframe(sample_cruise, use_container_width=True)
        st.caption("☝️ Expected format (click 'Use Sample' below to load sample data)")

        col1, col2 = st.columns(2)
        with col1:
            cruise_file = st.file_uploader("Upload Cruise CSV", type=["csv"], key="cruise_upload")
            if cruise_file:
                cdf = pd.read_csv(cruise_file)
                cdf["Date"] = pd.to_datetime(cdf["Date"])
                cdf["Month"] = cdf["Date"].dt.strftime("%Y-%m")
                st.session_state.cruise_df = cdf
                st.success(f"✅ Cruise schedule loaded: {len(cdf)} sailings")
        with col2:
            if st.button("📋 Use Sample Cruise Data"):
                sample_cruise["Date"] = pd.to_datetime(sample_cruise["Date"])
                sample_cruise["Month"] = sample_cruise["Date"].dt.strftime("%Y-%m")
                st.session_state.cruise_df = sample_cruise
                st.success("✅ Sample cruise data loaded!")

    with tab3:
        st.subheader("🌤 Weather History")
        st.info("Upload a CSV with columns: `Date`, `Temperature`, `Precipitation_mm`, `Condition`")
        weather_file = st.file_uploader("Upload Weather CSV", type=["csv"], key="weather_upload")
        if weather_file:
            wdf = pd.read_csv(weather_file)
            st.success(f"✅ Weather data loaded: {len(wdf)} records")
            st.dataframe(wdf.head(), use_container_width=True)

    with tab4:
        st.subheader("📋 Current Inventory / Stock Levels")
        st.info("Upload a CSV with columns: `Item Number`, `Description`, `Qty On Hand`, `Branch`")
        inv_file = st.file_uploader("Upload Inventory CSV", type=["csv"], key="inv_upload")
        if inv_file:
            idf = pd.read_csv(inv_file)
            st.session_state.inventory_df = idf
            st.success(f"✅ Inventory loaded: {len(idf)} items")
            st.dataframe(idf.head(10), use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📊 Dashboard":
    st.title("📊 Dashboard")
    df = get_active_df()

    if df is None:
        st.warning("No data loaded. Please upload Sales History files in 📤 Data Hub.")
        st.stop()

    branch_label = "All Branches" if selected_branch == "ALL" else f"Branch {selected_branch}"
    st.subheader(f"📍 {branch_label} — Overview")

    # KPI row
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Total Items",    f"{len(df):,}")
    col2.metric("Total Units Sold", f"{df['Number Sold'].sum():,}")
    col3.metric("Total Revenue",  f"${df['Selling'].sum():,.0f}")
    col4.metric("Total Profit",   f"${df['Profit'].sum():,.0f}")
    avg_margin = df[df['Margin'] > 0]['Margin'].mean()
    col5.metric("Avg Margin",     f"{avg_margin:.1f}%")

    st.markdown("---")

    col_l, col_r = st.columns(2)

    with col_l:
        # Top 15 by revenue
        top_rev = df.nlargest(15, "Selling")[["Description","Selling","Profit","Number Sold"]]
        fig = px.bar(top_rev, x="Selling", y="Description", orientation="h",
                     title="Top 15 Items by Revenue",
                     color="Profit", color_continuous_scale="Teal",
                     labels={"Selling":"Revenue ($)","Description":""})
        fig.update_layout(height=500, yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig, use_container_width=True)

    with col_r:
        # Velocity distribution
        df["Velocity"] = df["Number Sold"].apply(classify_velocity)
        vel_counts = df["Velocity"].value_counts().reset_index()
        vel_counts.columns = ["Velocity","Count"]
        fig2 = px.pie(vel_counts, names="Velocity", values="Count",
                      title="Item Velocity Distribution",
                      hole=0.4)
        st.plotly_chart(fig2, use_container_width=True)

    # Margin scatter
    fig3 = px.scatter(
        df[df["Number Sold"] > 0],
        x="Number Sold", y="Margin",
        hover_data=["Description","Item Number"],
        title="Sales Volume vs. Margin — All Items",
        color="Margin", color_continuous_scale="RdYlGn",
        labels={"Number Sold":"Units Sold","Margin":"Margin %"},
        opacity=0.6
    )
    fig3.add_hline(y=0, line_dash="dash", line_color="red", annotation_text="Zero margin")
    st.plotly_chart(fig3, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: FORECAST & REORDER
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🔮 Forecast & Reorder":
    st.title("🔮 Forecast & Reorder Suggestions")
    df = get_active_df()

    if df is None:
        st.warning("No data loaded. Please upload Sales History files in 📤 Data Hub.")
        st.stop()

    with st.expander("⚙️ Forecast Settings", expanded=True):
        col1, col2, col3 = st.columns(3)
        reorder_weeks    = col1.slider("Reorder window (weeks)", 2, 12, 4)
        safety_pct       = col2.slider("Safety stock %", 0, 50, 15)
        min_margin_show  = col3.slider("Min margin to show (%)", -200, 0, -100)

    # Build reorder list
    rdf = build_reorder(
        df, st.session_state.cruise_df,
        reorder_weeks, safety_pct,
        st.session_state.custom_exclude_keywords,
        st.session_state.custom_exclude_items
    )
    st.session_state.reorder_df = rdf

    # Filter toggles
    st.markdown("---")
    col_a, col_b, col_c = st.columns(3)
    show_excluded  = col_a.checkbox("Show excluded items", False)
    priority_filter = col_b.multiselect("Filter priority",
        ["🚨 URGENT","⚠️ WARNING","✅ OK","❌ EXCLUDED"],
        default=["🚨 URGENT","⚠️ WARNING"])
    search_term = col_c.text_input("🔍 Search description")

    display_df = rdf.copy()
    if not show_excluded:
        display_df = display_df[display_df["Priority"] != "❌ EXCLUDED"]
    if priority_filter:
        display_df = display_df[display_df["Priority"].isin(priority_filter)]
    if search_term:
        display_df = display_df[
            display_df["Description"].str.lower().str.contains(search_term.lower(), na=False)]

    # Stats
    urgent_n  = len(rdf[rdf["Priority"] == "🚨 URGENT"])
    warning_n = len(rdf[rdf["Priority"] == "⚠️ WARNING"])
    excl_n    = len(rdf[rdf["Priority"] == "❌ EXCLUDED"])
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("🚨 URGENT", urgent_n)
    c2.metric("⚠️ WARNING", warning_n)
    c3.metric("✅ OK", len(rdf[rdf["Priority"] == "✅ OK"]))
    c4.metric("❌ Excluded", excl_n)

    st.markdown(f"**Showing {len(display_df):,} items**")

    st.dataframe(
        display_df[["Priority","Item #","Description","Brand","Velocity",
                    "Total Sold","Avg/Week","Seasonal Idx","Cruise Mult",
                    "Suggested Order","Margin %","Exclusion Reason","Branch"]],
        use_container_width=True,
        height=500
    )

    # Download
    csv_out = display_df.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Download Reorder List (CSV)", csv_out,
                       "reorder_suggestions.csv", "text/csv")

    # Excluded items detail
    if show_excluded:
        st.markdown("---")
        st.subheader("❌ Excluded Items Detail")
        excl_df = rdf[rdf["Priority"] == "❌ EXCLUDED"][
            ["Item #","Description","Total Sold","Margin %","Exclusion Reason"]]
        st.dataframe(excl_df, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: QA AGENT CHAT
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🤖 QA Agent Chat":
    st.title("🤖 Reorder QA Agent")
    st.caption("Ask me anything about your reorder list, exclusions, top sellers, or cruise prep.")

    if st.session_state.reorder_df is None:
        st.warning("Go to **🔮 Forecast & Reorder** first to generate the reorder list, then come back here.")
        st.stop()

    # Chat display
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Input
    user_input = st.chat_input("Ask the agent...")
    if user_input:
        st.session_state.chat_history.append({"role":"user","content":user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        reply, st.session_state.custom_exclude_keywords, st.session_state.custom_exclude_items = agent_respond(
            user_input,
            st.session_state.reorder_df,
            st.session_state.custom_exclude_keywords,
            st.session_state.custom_exclude_items,
            get_active_df()
        )

        st.session_state.chat_history.append({"role":"assistant","content":reply})
        with st.chat_message("assistant"):
            st.markdown(reply)

    if st.button("🗑 Clear chat"):
        st.session_state.chat_history = []
        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: ANALYTICS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📈 Analytics":
    st.title("📈 Analytics")
    df = get_active_df()

    if df is None:
        st.warning("No data loaded.")
        st.stop()

    tab1, tab2, tab3 = st.tabs(["🏆 Top Performers", "🔮 Seasonal Forecast", "🏪 Brand Analysis"])

    with tab1:
        n = st.slider("Show top N items", 10, 50, 20)
        metric = st.selectbox("Rank by", ["Selling","Number Sold","Profit","Margin"])
        top_df = df[df["Number Sold"] > 0].nlargest(n, metric)
        fig = px.bar(top_df, x=metric, y="Description", orientation="h",
                     title=f"Top {n} Items by {metric}",
                     color="Margin", color_continuous_scale="Viridis")
        fig.update_layout(height=600, yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        st.subheader("📅 Seasonal Forecast — Next 12 Months")
        base_weekly = df["Number Sold"].sum() / 52
        months = []
        for i in range(1, 13):
            mo = (CURRENT_MONTH + i - 1) % 12 + 1
            yr = CURRENT_YEAR + ((CURRENT_MONTH + i - 1) // 12)
            idx = SEASONAL_INDEX[mo]
            months.append({
                "Month": f"{yr}-{mo:02d}",
                "Seasonal Index": idx,
                "Forecast Units": round(base_weekly * 4.33 * idx)
            })
        season_df = pd.DataFrame(months)
        fig_s = px.bar(season_df, x="Month", y="Forecast Units",
                       color="Seasonal Index", color_continuous_scale="RdYlGn",
                       title="12-Month Demand Forecast (NL Tourism Seasonal Model)")
        fig_s.add_scatter(x=season_df["Month"], y=season_df["Forecast Units"],
                          mode="lines+markers", name="Trend", line=dict(color="navy", width=2))
        st.plotly_chart(fig_s, use_container_width=True)

        if st.session_state.cruise_df is not None:
            st.subheader("🚢 Cruise Impact Calendar")
            cdf = st.session_state.cruise_df.copy()
            cdf["Month"] = cdf["Date"].dt.to_period("M").astype(str)
            monthly = cdf.groupby("Month")["Passengers"].sum().reset_index()
            fig_c = px.bar(monthly, x="Month", y="Passengers",
                           title="Monthly Cruise Passenger Volume",
                           color="Passengers", color_continuous_scale="Blues")
            st.plotly_chart(fig_c, use_container_width=True)

    with tab3:
        brand_df = (df.groupby("Brand")
                      .agg({"Number Sold":"sum","Selling":"sum","Profit":"sum"})
                      .reset_index()
                      .nlargest(20, "Selling"))
        fig_b = px.bar(brand_df, x="Selling", y="Brand", orientation="h",
                       title="Top 20 Brands by Revenue",
                       color="Profit", color_continuous_scale="Teal")
        fig_b.update_layout(height=600, yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig_b, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: SETTINGS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "⚙️ Settings":
    st.title("⚙️ Exclusion Rules & Settings")

    st.subheader("🚫 Built-in Exclusion Rules (always active)")
    st.info("These rules are hardcoded and cannot be removed.")
    for kw in EXCLUDE_KEYWORDS:
        st.markdown(f"- `{kw}`")

    st.markdown("---")
    st.subheader("📅 Dated Item Rules")
    st.success(f"Any item matching keywords {DATED_KEYWORDS} with a year < {CURRENT_YEAR} "
               f"is automatically excluded. Calendars for year {CURRENT_YEAR} are excluded after March.")

    st.markdown("---")
    st.subheader("➕ Custom Exclusion Keywords")
    new_kw = st.text_input("Add keyword to exclude (e.g. 'sale poster', 'damaged')")
    if st.button("➕ Add Rule"):
        if new_kw and new_kw.lower() not in st.session_state.custom_exclude_keywords:
            st.session_state.custom_exclude_keywords.append(new_kw.lower())
            st.success(f"Rule added: '{new_kw}'")

    if st.session_state.custom_exclude_keywords:
        st.markdown("**Active custom rules:**")
        for i, kw in enumerate(st.session_state.custom_exclude_keywords):
            col1, col2 = st.columns([4,1])
            col1.markdown(f"- `{kw}`")
            if col2.button("🗑", key=f"del_{i}"):
                st.session_state.custom_exclude_keywords.pop(i)
                st.rerun()
    else:
        st.info("No custom rules added yet.")

    st.markdown("---")
    st.subheader("🔢 Exclude Specific Item Numbers")
    new_item = st.text_input("Add Item Number to exclude (e.g. 107114)")
    if st.button("➕ Add Item Exclusion"):
        if new_item and new_item not in st.session_state.custom_exclude_items:
            st.session_state.custom_exclude_items.append(new_item)
            st.success(f"Item {new_item} excluded.")

    if st.session_state.custom_exclude_items:
        st.markdown("**Excluded item numbers:**")
        st.write(", ".join(st.session_state.custom_exclude_items))
