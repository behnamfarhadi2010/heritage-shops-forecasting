import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import re
import io
import csv as _csv
from datetime import datetime, date

st.set_page_config(
    page_title="Heritage Shops — Inventory & Forecast",
    page_icon="🏪",
    layout="wide",
    initial_sidebar_state="expanded",
)

CURRENT_YEAR  = datetime.now().year
CURRENT_MONTH = datetime.now().month

SEASONAL_INDEX = {
    1:0.35, 2:0.35, 3:0.40, 4:0.55, 5:0.75, 6:1.20,
    7:2.50, 8:2.40, 9:1.50, 10:0.90, 11:0.55, 12:0.80
}

EXCLUDE_KEYWORDS = [
    "shipping charges", "environmental charge", "gift card",
    "gift certificate", "poster tube", "st-receive",
    "clearance", "discontinued", "out of print"
]
DATED_KEYWORDS = ["calendar", "planner", "diary", "agenda", "almanac"]


# ══════════════════════════════════════════════════════════════════════════════
# CSV PARSER  — handles real comma-separated POS export
# ══════════════════════════════════════════════════════════════════════════════
def parse_csv(uploaded_file):
    content = uploaded_file.read().decode("utf-8", errors="replace")
    lines   = content.splitlines()

    branch    = "Unknown"
    date_from = ""
    date_to   = ""

    for line in lines[:15]:
        if line.startswith("Branch:"):
            m = re.search(r"Branch:\s*(\d+)", line)
            if m:
                branch = m.group(1)
        if "Date Range" in line:
            m = re.search(r"From[:\s]+(\S+)\s+To[:\s]+(\S+)", line)
            if m:
                date_from = m.group(1)
                date_to   = m.group(2).split(",")[0]

    data_rows = []
    in_data   = False

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("Item Number"):
            in_data = True
            continue

        if stripped.startswith("Supplier,Product") or stripped.startswith("Supplier Product"):
            in_data = False
            continue

        if not in_data or not stripped:
            continue

        if stripped.startswith(","):
            continue

        reader = _csv.reader(io.StringIO(stripped))
        try:
            row = next(reader)
        except StopIteration:
            continue

        while len(row) < 12:
            row.append("")

        item_num = row[0].strip()
        if not item_num or not re.match(r"^\d+$", item_num):
            continue

        try:
            data_rows.append({
                "Item Number":  item_num,
                "Department":   row[1].strip(),
                "Brand":        row[2].strip(),
                "Supplier":     row[3].strip(),
                "Desc Code":    row[4].strip(),
                "Description":  row[5].strip(),
                "Supp Cat":     row[6].strip(),
                "Number Sold":  int(float(row[7])) if row[7].strip() else 0,
                "Selling":      float(row[8])       if row[8].strip() else 0.0,
                "Cost":         float(row[9])       if row[9].strip() else 0.0,
                "Profit":       float(row[10])      if row[10].strip() else 0.0,
                "Margin":       float(row[11])      if row[11].strip() else 0.0,
            })
        except (ValueError, IndexError):
            continue

    if not data_rows:
        return None, branch, date_from, date_to

    df = pd.DataFrame(data_rows)
    df["Branch"] = branch
    return df, branch, date_from, date_to


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def classify_velocity(sold):
    if sold >= 50: return "🔥 Fast"
    if sold >= 10: return "⚡ Medium"
    if sold >= 1:  return "🐢 Slow"
    return "💀 Dead"


def get_exclusion_reason(desc, item_num, margin, sold, custom_kw, custom_items):
    desc_lower = desc.lower()

    if str(item_num) in custom_items:
        return "Manually excluded"

    for kw in (custom_kw + EXCLUDE_KEYWORDS):
        if kw.lower() in desc_lower:
            return f"Service/excluded keyword: '{kw}'"

    for kw in DATED_KEYWORDS:
        if kw in desc_lower:
            year_m = re.search(r"\b(20\d{2})\b", desc)
            if year_m:
                item_year = int(year_m.group(1))
                if item_year < CURRENT_YEAR:
                    return f"Dated item ({item_year} < {CURRENT_YEAR})"
                elif item_year == CURRENT_YEAR and CURRENT_MONTH > 3:
                    return f"Calendar {item_year} — season passed"

    if margin < 0:
        return f"Negative margin ({margin:.1f}%)"

    if sold == 0:
        return "Zero sales — potential dead stock"

    return None


def build_reorder(df, cruise_df, reorder_weeks, safety_pct, custom_kw, custom_items):
    next_month = (CURRENT_MONTH % 12) + 1
    seasonal   = SEASONAL_INDEX.get(next_month, 1.0)

    cruise_mult = 1.0
    if cruise_df is not None and not cruise_df.empty:
        nm = f"{CURRENT_YEAR}-{next_month:02d}"
        if "Month" in cruise_df.columns and "Passengers" in cruise_df.columns:
            pax = cruise_df[cruise_df["Month"] == nm]["Passengers"].sum()
            if pax > 5000:   cruise_mult = 1.35
            elif pax > 2000: cruise_mult = 1.20
            elif pax > 0:    cruise_mult = 1.10

    rows = []
    for _, r in df.iterrows():
        reason     = get_exclusion_reason(
            r["Description"], r["Item Number"], r["Margin"],
            r["Number Sold"], custom_kw, custom_items)
        sold       = r["Number Sold"]
        avg_weekly = sold / 52.0
        forecast   = avg_weekly * reorder_weeks * seasonal * cruise_mult
        safety     = forecast * (safety_pct / 100)
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
            "Priority":        priority,
            "Item #":          r["Item Number"],
            "Description":     r["Description"],
            "Brand":           r.get("Brand", ""),
            "Dept":            r.get("Department", ""),
            "Velocity":        velocity,
            "Total Sold":      sold,
            "Avg/Week":        round(avg_weekly, 1),
            "Seasonal Idx":    seasonal,
            "Cruise Mult":     round(cruise_mult, 2),
            "Forecast Qty":    round(forecast, 1),
            "Suggested Order": suggested,
            "Margin %":        r["Margin"],
            "Exclusion Reason":reason or "",
            "Branch":          r.get("Branch", ""),
        })
    return pd.DataFrame(rows)


# ══════════════════════════════════════════════════════════════════════════════
# QA AGENT
# ══════════════════════════════════════════════════════════════════════════════
def agent_respond(user_msg, reorder_df, custom_kw, custom_items, context_df):
    msg   = user_msg.lower().strip()
    reply = ""

    for trigger in ["why is", "why was", "explain"]:
        if trigger in msg:
            token = msg.split(trigger)[-1].strip().rstrip("?").strip()
            matches = reorder_df[
                reorder_df["Description"].str.lower().str.contains(token, na=False) |
                reorder_df["Item #"].astype(str).str.contains(token, na=False)
            ]
            if not matches.empty:
                row  = matches.iloc[0]
                excl = row["Exclusion Reason"]
                if excl:
                    reply = (
                        f"**{row['Description']}** (Item #{row['Item #']}) is **excluded**.\n\n"
                        f"**Reason:** _{excl}_\n\n"
                        f"It has been automatically removed from reorder suggestions."
                    )
                else:
                    reply = (
                        f"**{row['Description']}** (Item #{row['Item #']}) — Priority: **{row['Priority']}**\n\n"
                        f"- Total Sold: {row['Total Sold']}\n"
                        f"- Velocity: {row['Velocity']}\n"
                        f"- Seasonal Index: {row['Seasonal Idx']}x\n"
                        f"- Cruise Multiplier: {row['Cruise Mult']}x\n"
                        f"- Suggested Order: **{row['Suggested Order']} units**"
                    )
            else:
                reply = f"I couldn't find an item matching **'{token}'** in the current reorder list."
            return reply, custom_kw, custom_items

    if any(x in msg for x in ["exclude", "block", "remove", "never suggest"]):
        kw_match = re.search(r"[\"'](.*?)[\"']", msg)
        if kw_match:
            new_kw = kw_match.group(1).lower()
            if new_kw not in custom_kw:
                custom_kw.append(new_kw)
            reply = (
                f"Rule added: items containing **'{new_kw}'** will now be excluded.\n\n"
                f"Go to **Forecast & Reorder** and refresh to see the updated list."
            )
        else:
            reply = "Put the keyword in quotes. Example: `exclude 'sale poster'`"
        return reply, custom_kw, custom_items

    if "urgent" in msg or "critical" in msg:
        urgent = reorder_df[reorder_df["Priority"] == "🚨 URGENT"]
        if urgent.empty:
            reply = "No URGENT items found with current settings."
        else:
            top   = urgent[["Item #", "Description", "Suggested Order"]].head(10)
            reply = f"**URGENT items ({len(urgent)} total — top 10):**\n\n" + top.to_markdown(index=False)
        return reply, custom_kw, custom_items

    if any(x in msg for x in ["top", "best seller", "best selling", "highest"]):
        if context_df is not None:
            top   = context_df.nlargest(10, "Number Sold")[["Item Number","Description","Number Sold","Margin"]]
            reply = "**Top 10 Best Sellers (by units sold):**\n\n" + top.to_markdown(index=False)
        else:
            reply = "No sales data loaded yet."
        return reply, custom_kw, custom_items

    if "cruise" in msg:
        souvenir_kws = ["magnet","postcard","keychain","ornament","bookmark",
                        "lapel","sticker","soapstone"]
        if context_df is not None:
            mask  = context_df["Description"].str.lower().apply(
                lambda d: any(kw in d for kw in souvenir_kws))
            items = context_df[mask].nlargest(15, "Number Sold")[
                ["Item Number","Description","Number Sold"]]
            reply = "**Top items for cruise week (souvenirs):**\n\n" + items.to_markdown(index=False)
        else:
            reply = "No sales data loaded. Upload a Sales History file first."
        return reply, custom_kw, custom_items

    if "rule" in msg or "exclusion" in msg:
        all_rules = EXCLUDE_KEYWORDS + custom_kw
        reply = "**Current exclusion rules:**\n\n" + "\n".join(f"- `{r}`" for r in all_rules)
        return reply, custom_kw, custom_items

    reply = (
        "Hi! I'm your Reorder QA Agent. Try asking:\n\n"
        "- **Why is [item name] excluded?**\n"
        "- **Why is [item name] in the list?**\n"
        "- **Show urgent items**\n"
        "- **Top sellers**\n"
        "- **What to order for cruise week**\n"
        "- **Exclude 'keyword'** — adds a new rule\n"
        "- **Show exclusion rules**\n"
    )
    return reply, custom_kw, custom_items


# ══════════════════════════════════════════════════════════════════════════════
# SESSION STATE
# ══════════════════════════════════════════════════════════════════════════════
defaults = {
    "sales_dfs":               {},
    "cruise_df":               None,
    "inventory_df":            None,
    "custom_exclude_keywords": [],
    "custom_exclude_items":    [],
    "chat_history":            [],
    "reorder_df":              None,
}
for key, val in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val


# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("## 🏪 Heritage Shops")
    st.markdown("Inventory & Forecast System")
    st.markdown("---")

    role = st.selectbox("👤 Role", ["Warehouse Manager", "Store Supervisor", "Web Store"])

    branches_loaded = list(st.session_state.sales_dfs.keys())
    if role == "Store Supervisor":
        selected_branch = st.selectbox(
            "🏪 Branch",
            branches_loaded if branches_loaded else ["(upload data first)"]
        )
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
    next_mo = (CURRENT_MONTH % 12) + 1
    st.caption(f"📅 Today: {date.today().strftime('%b %d, %Y')}")
    st.caption(f"🗓 Next month seasonal index: **{SEASONAL_INDEX.get(next_mo, 1.0)}x**")
    if st.session_state.cruise_df is not None:
        st.caption("🚢 Cruise data: **loaded**")
    else:
        st.caption("🚢 Cruise data: not loaded")


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
    st.markdown("Upload your data files. **Sales History** is required; all others are optional.")

    tab1, tab2, tab3, tab4 = st.tabs([
        "📦 Sales History", "🚢 Cruise Schedule", "🌤 Weather", "📋 Current Inventory"
    ])

    with tab1:
        st.subheader("Sales History CSV")
        st.info(
            "Accepts both **SalesHistoryReport** and **SalesHistoryByItemReport** exports. "
            "You can upload multiple files (one per branch) at once."
        )
        uploaded = st.file_uploader(
            "Upload Sales History CSV(s)", type=["csv"],
            accept_multiple_files=True, key="sales_upload"
        )
        if uploaded:
            for f in uploaded:
                df, branch, dfrom, dto = parse_csv(f)
                if df is not None and not df.empty:
                    st.session_state.sales_dfs[branch] = df
                    st.success(
                        f"✅ Branch **{branch}** — {len(df):,} items | "
                        f"{dfrom} → {dto}"
                    )
                else:
                    st.error(
                        f"❌ Could not parse **{f.name}**. "
                        f"Make sure it is a Heritage POS CSV export (SalesHistoryReport or SalesHistoryByItemReport)."
                    )

        if st.session_state.sales_dfs:
            st.markdown("### Loaded branches")
            for b, d in st.session_state.sales_dfs.items():
                st.markdown(
                    f"- Branch **{b}**: {len(d):,} items | "
                    f"{d['Number Sold'].sum():,} units sold | "
                    f"${d['Selling'].sum():,.0f} revenue"
                )
            if st.button("🗑 Clear all loaded data"):
                st.session_state.sales_dfs = {}
                st.rerun()

    with tab2:
        st.subheader("🚢 Cruise Ship Schedule")
        st.info("Upload a CSV with columns: `Date` (YYYY-MM-DD), `Ship Name`, `Passengers`")
        sample_cruise = pd.DataFrame({
            "Date":      ["2026-06-15","2026-06-22","2026-07-04","2026-07-11","2026-08-03"],
            "Ship Name": ["Norwegian Joy","Carnival Breeze","MSC Bellissima","Royal Caribbean","Celebrity Edge"],
            "Passengers":[4200, 3800, 5100, 4700, 3200]
        })
        st.dataframe(sample_cruise, use_container_width=True)
        col1, col2 = st.columns(2)
        with col1:
            cruise_file = st.file_uploader("Upload Cruise CSV", type=["csv"], key="cruise_upload")
            if cruise_file:
                cdf = pd.read_csv(cruise_file)
                cdf["Date"]  = pd.to_datetime(cdf["Date"])
                cdf["Month"] = cdf["Date"].dt.strftime("%Y-%m")
                st.session_state.cruise_df = cdf
                st.success(f"✅ {len(cdf)} sailings loaded")
        with col2:
            if st.button("📋 Use Sample Cruise Data"):
                sample_cruise["Date"]  = pd.to_datetime(sample_cruise["Date"])
                sample_cruise["Month"] = sample_cruise["Date"].dt.strftime("%Y-%m")
                st.session_state.cruise_df = sample_cruise.copy()
                st.success("✅ Sample cruise data loaded!")

    with tab3:
        st.subheader("🌤 Weather History")
        st.info("Upload a CSV with columns: `Date`, `Temperature`, `Precipitation_mm`, `Condition`")
        weather_file = st.file_uploader("Upload Weather CSV", type=["csv"], key="weather_upload")
        if weather_file:
            wdf = pd.read_csv(weather_file)
            st.success(f"✅ {len(wdf)} weather records loaded")
            st.dataframe(wdf.head(), use_container_width=True)

    with tab4:
        st.subheader("📋 Current Inventory")
        st.info("Upload a CSV with columns: `Item Number`, `Description`, `Qty On Hand`, `Branch`")
        inv_file = st.file_uploader("Upload Inventory CSV", type=["csv"], key="inv_upload")
        if inv_file:
            idf = pd.read_csv(inv_file)
            st.session_state.inventory_df = idf
            st.success(f"✅ {len(idf)} inventory items loaded")
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

    label = "All Branches" if selected_branch == "ALL" else f"Branch {selected_branch}"
    st.subheader(f"📍 {label} — Overview")

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Items",   f"{len(df):,}")
    c2.metric("Units Sold",    f"{df['Number Sold'].sum():,}")
    c3.metric("Total Revenue", f"${df['Selling'].sum():,.0f}")
    c4.metric("Total Profit",  f"${df['Profit'].sum():,.0f}")
    pos = df[df["Margin"] > 0]["Margin"].mean()
    c5.metric("Avg Margin",    f"{pos:.1f}%")

    st.markdown("---")
    col_l, col_r = st.columns(2)

    with col_l:
        top_rev = df.nlargest(15, "Selling")[["Description","Selling","Profit","Number Sold"]]
        fig = px.bar(top_rev, x="Selling", y="Description", orientation="h",
                     title="Top 15 Items by Revenue",
                     color="Profit", color_continuous_scale="Teal",
                     labels={"Selling":"Revenue ($)","Description":""})
        fig.update_layout(height=500, yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig, use_container_width=True)

    with col_r:
        df["Velocity"] = df["Number Sold"].apply(classify_velocity)
        vel = df["Velocity"].value_counts().reset_index()
        vel.columns = ["Velocity","Count"]
        fig2 = px.pie(vel, names="Velocity", values="Count",
                      title="Item Velocity Distribution", hole=0.4)
        st.plotly_chart(fig2, use_container_width=True)

    fig3 = px.scatter(
        df[df["Number Sold"] > 0],
        x="Number Sold", y="Margin",
        hover_data=["Description","Item Number"],
        title="Sales Volume vs. Margin",
        color="Margin", color_continuous_scale="RdYlGn", opacity=0.6
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
        col1, col2 = st.columns(2)
        reorder_weeks = col1.slider("Reorder window (weeks)", 2, 12, 4)
        safety_pct    = col2.slider("Safety stock %", 0, 50, 15)

    rdf = build_reorder(
        df, st.session_state.cruise_df,
        reorder_weeks, safety_pct,
        st.session_state.custom_exclude_keywords,
        st.session_state.custom_exclude_items
    )
    st.session_state.reorder_df = rdf

    st.markdown("---")
    col_a, col_b, col_c = st.columns(3)
    show_excluded   = col_a.checkbox("Show excluded items", False)
    priority_filter = col_b.multiselect(
        "Filter priority",
        ["🚨 URGENT","⚠️ WARNING","✅ OK","❌ EXCLUDED"],
        default=["🚨 URGENT","⚠️ WARNING"]
    )
    search_term = col_c.text_input("🔍 Search description")

    display_df = rdf.copy()
    if not show_excluded:
        display_df = display_df[display_df["Priority"] != "❌ EXCLUDED"]
    if priority_filter:
        display_df = display_df[display_df["Priority"].isin(priority_filter)]
    if search_term:
        display_df = display_df[
            display_df["Description"].str.lower().str.contains(search_term.lower(), na=False)
        ]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🚨 URGENT",  len(rdf[rdf["Priority"] == "🚨 URGENT"]))
    c2.metric("⚠️ WARNING", len(rdf[rdf["Priority"] == "⚠️ WARNING"]))
    c3.metric("✅ OK",       len(rdf[rdf["Priority"] == "✅ OK"]))
    c4.metric("❌ Excluded", len(rdf[rdf["Priority"] == "❌ EXCLUDED"]))

    st.markdown(f"**Showing {len(display_df):,} items**")
    st.dataframe(
        display_df[[
            "Priority","Item #","Description","Brand","Velocity",
            "Total Sold","Avg/Week","Seasonal Idx","Cruise Mult",
            "Suggested Order","Margin %","Exclusion Reason","Branch"
        ]],
        use_container_width=True, height=500
    )

    csv_out = display_df.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Download Reorder List (CSV)", csv_out,
                       "reorder_suggestions.csv", "text/csv")

    if show_excluded:
        st.markdown("---")
        st.subheader("❌ Excluded Items Detail")
        excl_df = rdf[rdf["Priority"] == "❌ EXCLUDED"][[
            "Item #","Description","Total Sold","Margin %","Exclusion Reason"
        ]]
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

    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

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
        n      = st.slider("Show top N items", 10, 50, 20)
        metric = st.selectbox("Rank by", ["Selling","Number Sold","Profit","Margin"])
        top_df = df[df["Number Sold"] > 0].nlargest(n, metric)
        fig    = px.bar(top_df, x=metric, y="Description", orientation="h",
                        title=f"Top {n} Items by {metric}",
                        color="Margin", color_continuous_scale="Viridis")
        fig.update_layout(height=600, yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        st.subheader("📅 Seasonal Forecast — Next 12 Months")
        base_weekly = df["Number Sold"].sum() / 52
        months = []
        for i in range(1, 13):
            mo  = (CURRENT_MONTH + i - 1) % 12 + 1
            yr  = CURRENT_YEAR + ((CURRENT_MONTH + i - 1) // 12)
            idx = SEASONAL_INDEX[mo]
            months.append({
                "Month":          f"{yr}-{mo:02d}",
                "Seasonal Index": idx,
                "Forecast Units": round(base_weekly * 4.33 * idx)
            })
        sdf   = pd.DataFrame(months)
        fig_s = px.bar(sdf, x="Month", y="Forecast Units",
                       color="Seasonal Index", color_continuous_scale="RdYlGn",
                       title="12-Month Demand Forecast (NL Tourism Seasonal Model)")
        fig_s.add_scatter(x=sdf["Month"], y=sdf["Forecast Units"],
                          mode="lines+markers", name="Trend",
                          line=dict(color="navy", width=2))
        st.plotly_chart(fig_s, use_container_width=True)

        if st.session_state.cruise_df is not None:
            st.subheader("🚢 Cruise Passenger Calendar")
            cdf     = st.session_state.cruise_df.copy()
            monthly = cdf.groupby("Month")["Passengers"].sum().reset_index()
            fig_c   = px.bar(monthly, x="Month", y="Passengers",
                             title="Monthly Cruise Passenger Volume",
                             color="Passengers", color_continuous_scale="Blues")
            st.plotly_chart(fig_c, use_container_width=True)

    with tab3:
        brand_df = (
            df.groupby("Brand")
              .agg({"Number Sold":"sum","Selling":"sum","Profit":"sum"})
              .reset_index()
              .nlargest(20, "Selling")
        )
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

    st.subheader("🔒 Built-in Rules (always active)")
    for kw in EXCLUDE_KEYWORDS:
        st.markdown(f"- `{kw}`")

    st.markdown("---")
    st.subheader("📅 Dated Item Rule")
    st.success(
        f"Items matching {DATED_KEYWORDS} with a year < {CURRENT_YEAR} are auto-excluded. "
        f"Year {CURRENT_YEAR} calendars excluded after March."
    )

    st.markdown("---")
    st.subheader("➕ Custom Exclusion Keywords")
    new_kw = st.text_input("Add keyword to exclude")
    if st.button("➕ Add Rule") and new_kw:
        if new_kw.lower() not in st.session_state.custom_exclude_keywords:
            st.session_state.custom_exclude_keywords.append(new_kw.lower())
            st.success(f"Rule added: '{new_kw}'")

    if st.session_state.custom_exclude_keywords:
        for i, kw in enumerate(st.session_state.custom_exclude_keywords):
            col1, col2 = st.columns([5, 1])
            col1.markdown(f"- `{kw}`")
            if col2.button("🗑", key=f"del_kw_{i}"):
                st.session_state.custom_exclude_keywords.pop(i)
                st.rerun()
    else:
        st.info("No custom rules added yet.")

    st.markdown("---")
    st.subheader("🔢 Exclude Specific Item Numbers")
    new_item = st.text_input("Add Item Number to exclude (e.g. 107114)")
    if st.button("➕ Add Item") and new_item:
        if new_item not in st.session_state.custom_exclude_items:
            st.session_state.custom_exclude_items.append(new_item)
            st.success(f"Item {new_item} excluded.")

    if st.session_state.custom_exclude_items:
        st.markdown("**Excluded item numbers:** " +
                    ", ".join(f"`{i}`" for i in st.session_state.custom_exclude_items))
    else:
        st.info("No specific items excluded yet.")
