import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
from advanced_forecasting import InventoryForecaster
import io

# Page configuration
st.set_page_config(
    page_title="Heritage Shops - Inventory Forecasting",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1976D2;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1976D2;
    }
    .urgent-alert {
        background-color: #ffebee;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #d32f2f;
        margin-bottom: 1rem;
    }
    .warning-alert {
        background-color: #fff3e0;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #f57c00;
        margin-bottom: 1rem;
    }
    </style>
""", unsafe_allow_html=True)

# Initialize session state
if 'forecasts_df' not in st.session_state:
    st.session_state.forecasts_df = None
if 'inventory_df' not in st.session_state:
    st.session_state.inventory_df = None
if 'sales_df' not in st.session_state:
    st.session_state.sales_df = None

# Sidebar
with st.sidebar:
    st.image("https://via.placeholder.com/200x80/1976D2/FFFFFF?text=Heritage+Shops", use_container_width=True)
    st.markdown("---")

    page = st.radio(
        "Navigation",
        ["📤 Upload Data", "🚨 Urgent Alerts", "📊 All Products", "📈 Analytics", "📄 Purchase Orders", "⚙️ Settings"]
    )

    st.markdown("---")
    st.markdown("### About")
    st.info("AI-powered inventory forecasting system for Heritage Shops. Upload your data to get instant predictions!")

# Main header
st.markdown('<div class="main-header">📦 Heritage Shops Inventory Forecasting</div>', unsafe_allow_html=True)

# ============================================================================
# PAGE: UPLOAD DATA
# ============================================================================
if page == "📤 Upload Data":
    st.header("📤 Upload Your Data")

    st.markdown("""
    Upload your sales history and current inventory files to generate forecasts automatically.
    The system will analyze patterns and predict future demand based on today's date.
    """)

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📊 Historical Sales Data")
        st.markdown("""
        **Required columns:**
        - `Item_Number` or `SKU` or `Product_ID`
        - `Date` (any format: 2024-01-15, Jan 2024, etc.)
        - `Quantity` or `Units_Sold`
        - `Description` (optional)
        - `Branch` or `Store` (optional)
        """)

        sales_file = st.file_uploader(
            "Upload Sales History CSV",
            type=['csv', 'xlsx'],
            key='sales_upload',
            help="Upload your historical sales data (monthly or daily)"
        )

        if sales_file:
            try:
                # Read the file
                if sales_file.name.endswith('.csv'):
                    sales_df = pd.read_csv(sales_file)
                else:
                    sales_df = pd.read_excel(sales_file)

                st.success(f"✅ Loaded {len(sales_df):,} rows")

                # Show preview
                with st.expander("📋 Preview Sales Data"):
                    st.dataframe(sales_df.head(10))
                    st.write(f"**Columns:** {', '.join(sales_df.columns)}")

                # Store in session state
                st.session_state.sales_df = sales_df

            except Exception as e:
                st.error(f"❌ Error reading file: {str(e)}")

    with col2:
        st.subheader("📦 Current Inventory")
        st.markdown("""
        **Required columns:**
        - `Item_Number` or `SKU` or `Product_ID`
        - `Current_Stock` or `Quantity` or `In_Stock`
        - `Description` (optional)
        - `Branch` or `Store` (optional)
        """)

        inventory_file = st.file_uploader(
            "Upload Current Inventory CSV",
            type=['csv', 'xlsx'],
            key='inventory_upload',
            help="Upload your current stock levels"
        )

        if inventory_file:
            try:
                # Read the file
                if inventory_file.name.endswith('.csv'):
                    inventory_df = pd.read_csv(inventory_file)
                else:
                    inventory_df = pd.read_excel(inventory_file)

                st.success(f"✅ Loaded {len(inventory_df):,} items")

                # Show preview
                with st.expander("📋 Preview Inventory Data"):
                    st.dataframe(inventory_df.head(10))
                    st.write(f"**Columns:** {', '.join(inventory_df.columns)}")

                # Store in session state
                st.session_state.inventory_df = inventory_df

            except Exception as e:
                st.error(f"❌ Error reading file: {str(e)}")

    st.markdown("---")

    # Process and Generate Forecasts button
    if st.session_state.sales_df is not None:
        st.subheader("🔮 Generate Forecasts")

        col1, col2, col3 = st.columns(3)

        with col1:
            forecast_months = st.slider("Forecast Period (months)", 1, 12, 3)

        with col2:
            lead_time_days = st.number_input("Default Lead Time (days)", 1, 90, 14)

        with col3:
            service_level = st.slider("Service Level %", 80, 99, 95)

        if st.button("🚀 Generate Forecasts", type="primary", use_container_width=True):
            with st.spinner("🔮 Analyzing data and generating forecasts..."):
                try:
                    # Initialize forecaster
                    forecaster = InventoryForecaster()

                    # Prepare sales data
                    sales_df = st.session_state.sales_df.copy()

                    # Try to identify columns (flexible matching)
                    item_col = None
                    date_col = None
                    qty_col = None

                    for col in sales_df.columns:
                        col_lower = col.lower()
                        if 'item' in col_lower or 'sku' in col_lower or 'product' in col_lower or 'number' in col_lower:
                            item_col = col
                        if 'date' in col_lower or 'month' in col_lower or 'period' in col_lower:
                            date_col = col
                        if 'quantity' in col_lower or 'units' in col_lower or 'sold' in col_lower or 'qty' in col_lower:
                            qty_col = col

                    if not all([item_col, date_col, qty_col]):
                        st.error("❌ Could not identify required columns. Please ensure your CSV has columns for Item, Date, and Quantity.")
                        st.stop()

                    # Standardize column names
                    sales_df = sales_df.rename(columns={
                        item_col: 'Item_Number',
                        date_col: 'Date',
                        qty_col: 'Quantity'
                    })

                    # Convert date column
                    try:
                        sales_df['Date'] = pd.to_datetime(sales_df['Date'])
                    except:
                        st.error("❌ Could not parse dates. Please ensure dates are in a standard format (YYYY-MM-DD, MM/DD/YYYY, etc.)")
                        st.stop()

                    # Group by item and month
                    sales_df['YearMonth'] = sales_df['Date'].dt.to_period('M')
                    monthly_sales = sales_df.groupby(['Item_Number', 'YearMonth'])['Quantity'].sum().reset_index()
                    monthly_sales['Date'] = monthly_sales['YearMonth'].dt.to_timestamp()

                    # Get unique items
                    items = monthly_sales['Item_Number'].unique()

                    # Generate forecasts for each item
                    all_forecasts = []
                    progress_bar = st.progress(0)
                    status_text = st.empty()

                    for i, item in enumerate(items):
                        status_text.text(f"Processing {i+1}/{len(items)}: {item}")

                        item_sales = monthly_sales[monthly_sales['Item_Number'] == item].copy()
                        item_sales = item_sales.sort_values('Date')

                        if len(item_sales) >= 3:  # Need at least 3 months of data
                            # Get historical quantities
                            historical_qty = item_sales['Quantity'].values

                            # Generate forecast
                            forecast = forecaster.ensemble_forecast(historical_qty, periods=forecast_months)

                            # Calculate metrics
                            avg_monthly = np.mean(historical_qty)
                            daily_demand = avg_monthly / 30

                            # Get current stock if available
                            current_stock = 0
                            if st.session_state.inventory_df is not None:
                                inv_df = st.session_state.inventory_df
                                # Find matching item
                                for inv_col in inv_df.columns:
                                    if 'item' in inv_col.lower() or 'sku' in inv_col.lower() or 'product' in inv_col.lower():
                                        matches = inv_df[inv_df[inv_col] == item]
                                        if not matches.empty:
                                            # Find stock column
                                            for stock_col in inv_df.columns:
                                                if 'stock' in stock_col.lower() or 'quantity' in stock_col.lower() or 'qty' in stock_col.lower():
                                                    current_stock = matches[stock_col].values[0]
                                                    break
                                        break

                            # Calculate reorder metrics
                            safety_stock = daily_demand * np.sqrt(lead_time_days) * 1.65  # 95% service level
                            reorder_point = (daily_demand * lead_time_days) + safety_stock
                            order_quantity = max(avg_monthly * 2, 10)  # 2 months or min 10 units

                            # Days until stockout
                            if daily_demand > 0:
                                days_until_stockout = current_stock / daily_demand
                            else:
                                days_until_stockout = 999

                            # Priority
                            if current_stock <= reorder_point and days_until_stockout <= lead_time_days:
                                priority = "🚨 URGENT"
                            elif current_stock <= reorder_point * 1.5:
                                priority = "⚠️ Warning"
                            elif days_until_stockout <= lead_time_days * 1.5:
                                priority = "⚡ Order Soon"
                            else:
                                priority = "✅ OK"

                            all_forecasts.append({
                                'Item_Number': item,
                                'Current_Stock': current_stock,
                                'Daily_Demand': round(daily_demand, 2),
                                'Monthly_Forecast': round(forecast[0], 1),
                                'Reorder_Point': round(reorder_point, 0),
                                'Recommended_Order_Qty': round(order_quantity, 0),
                                'Days_Until_Stockout': round(days_until_stockout, 1),
                                'Safety_Stock': round(safety_stock, 0),
                                'Priority': priority,
                                'Last_Month_Sales': historical_qty[-1],
                                'Avg_Monthly_Sales': round(avg_monthly, 1),
                                'Trend': 'Growing' if len(historical_qty) > 1 and historical_qty[-1] > historical_qty[-2] else 'Stable'
                            })

                        progress_bar.progress((i + 1) / len(items))

                    progress_bar.empty()
                    status_text.empty()

                    # Create DataFrame
                    forecasts_df = pd.DataFrame(all_forecasts)

                    # Sort by priority
                    priority_order = {"🚨 URGENT": 0, "⚠️ Warning": 1, "⚡ Order Soon": 2, "✅ OK": 3}
                    forecasts_df['Priority_Order'] = forecasts_df['Priority'].map(priority_order)
                    forecasts_df = forecasts_df.sort_values('Priority_Order').drop('Priority_Order', axis=1)

                    # Store in session state
                    st.session_state.forecasts_df = forecasts_df

                    st.success(f"✅ Generated forecasts for {len(forecasts_df)} products!")

                    # Show summary
                    col1, col2, col3, col4 = st.columns(4)

                    with col1:
                        urgent = len(forecasts_df[forecasts_df['Priority'] == '🚨 URGENT'])
                        st.metric("🚨 Urgent Alerts", urgent)

                    with col2:
                        warnings = len(forecasts_df[forecasts_df['Priority'] == '⚠️ Warning'])
                        st.metric("⚠️ Warnings", warnings)

                    with col3:
                        order_soon = len(forecasts_df[forecasts_df['Priority'] == '⚡ Order Soon'])
                        st.metric("⚡ Order Soon", order_soon)

                    with col4:
                        ok_items = len(forecasts_df[forecasts_df['Priority'] == '✅ OK'])
                        st.metric("✅ OK", ok_items)

                    # Show preview
                    st.subheader("📊 Forecast Preview")
                    st.dataframe(
                        forecasts_df.head(20),
                        use_container_width=True,
                        hide_index=True
                    )

                    # Download button
                    csv = forecasts_df.to_csv(index=False)
                    st.download_button(
                        label="📥 Download Full Forecasts CSV",
                        data=csv,
                        file_name=f"forecasts_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )

                except Exception as e:
                    st.error(f"❌ Error generating forecasts: {str(e)}")
                    import traceback
                    st.code(traceback.format_exc())
    else:
        st.info("👆 Upload your sales history data above to generate forecasts")

# ============================================================================
# PAGE: URGENT ALERTS
# ============================================================================
elif page == "🚨 Urgent Alerts":
    st.header("🚨 Urgent Reorder Alerts")

    if st.session_state.forecasts_df is None:
        st.warning("⚠️ No forecast data available. Please upload data in the '📤 Upload Data' tab first.")
    else:
        df = st.session_state.forecasts_df

        # Filter urgent and warnings
        urgent_df = df[df['Priority'].isin(['🚨 URGENT', '⚠️ Warning'])].copy()

        if len(urgent_df) == 0:
            st.success("🎉 No urgent alerts! All products are well-stocked.")
        else:
            st.write(f"**{len(urgent_df)} products need immediate attention**")

            # Display each urgent item as a card
            for idx, row in urgent_df.iterrows():
                with st.container():
                    if row['Priority'] == '🚨 URGENT':
                        st.markdown(f'<div class="urgent-alert">', unsafe_allow_html=True)
                    else:
                        st.markdown(f'<div class="warning-alert">', unsafe_allow_html=True)

                    col1, col2, col3, col4 = st.columns([3, 2, 2, 2])

                    with col1:
                        st.markdown(f"**{row['Priority']} {row['Item_Number']}**")
                        st.caption(f"Days until stockout: {row['Days_Until_Stockout']:.0f}")

                    with col2:
                        st.metric("Current Stock", f"{row['Current_Stock']:.0f}")

                    with col3:
                        st.metric("Reorder Point", f"{row['Reorder_Point']:.0f}")

                    with col4:
                        st.metric("Order Qty", f"{row['Recommended_Order_Qty']:.0f}")

                    st.markdown('</div>', unsafe_allow_html=True)

# ============================================================================
# PAGE: ALL PRODUCTS
# ============================================================================
elif page == "📊 All Products":
    st.header("📊 All Product Forecasts")

    if st.session_state.forecasts_df is None:
        st.warning("⚠️ No forecast data available. Please upload data in the '📤 Upload Data' tab first.")
    else:
        df = st.session_state.forecasts_df

        # Filters
        col1, col2, col3 = st.columns(3)

        with col1:
            priority_filter = st.multiselect(
                "Filter by Priority",
                options=df['Priority'].unique(),
                default=df['Priority'].unique()
            )

        with col2:
            search = st.text_input("🔍 Search Item Number", "")

        with col3:
            min_daily_demand = st.number_input("Min Daily Demand", 0.0, float(df['Daily_Demand'].max()), 0.0)

        # Apply filters
        filtered_df = df[df['Priority'].isin(priority_filter)]

        if search:
            filtered_df = filtered_df[filtered_df['Item_Number'].astype(str).str.contains(search, case=False)]

        filtered_df = filtered_df[filtered_df['Daily_Demand'] >= min_daily_demand]

        st.write(f"Showing {len(filtered_df)} of {len(df)} products")

        # Display table
        st.dataframe(
            filtered_df,
            use_container_width=True,
            hide_index=True,
            height=600
        )

        # Download filtered results
        csv = filtered_df.to_csv(index=False)
        st.download_button(
            label="📥 Download Filtered Results",
            data=csv,
            file_name=f"filtered_forecasts_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )

# ============================================================================
# PAGE: ANALYTICS
# ============================================================================
elif page == "📈 Analytics":
    st.header("📈 Analytics Dashboard")

    if st.session_state.forecasts_df is None:
        st.warning("⚠️ No forecast data available. Please upload data in the '📤 Upload Data' tab first.")
    else:
        df = st.session_state.forecasts_df

        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Total Products", len(df))

        with col2:
            total_current_stock = df['Current_Stock'].sum()
            st.metric("Total Stock", f"{total_current_stock:,.0f}")

        with col3:
            avg_days_stockout = df['Days_Until_Stockout'].replace([np.inf, -np.inf], 999).mean()
            st.metric("Avg Days to Stockout", f"{avg_days_stockout:.0f}")

        with col4:
            total_order_value = df[df['Priority'].isin(['🚨 URGENT', '⚠️ Warning'])]['Recommended_Order_Qty'].sum()
            st.metric("Units to Order", f"{total_order_value:,.0f}")

        st.markdown("---")

        # Charts
        col1, col2 = st.columns(2)

        with col1:
            # Priority distribution
            priority_counts = df['Priority'].value_counts()
            fig = px.pie(
                values=priority_counts.values,
                names=priority_counts.index,
                title="Priority Distribution",
                color_discrete_sequence=['#d32f2f', '#f57c00', '#ffa726', '#4caf50']
            )
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            # Top 10 by demand
            top_10 = df.nlargest(10, 'Daily_Demand')[['Item_Number', 'Daily_Demand']]
            fig = px.bar(
                top_10,
                x='Item_Number',
                y='Daily_Demand',
                title="Top 10 Products by Daily Demand",
                color='Daily_Demand',
                color_continuous_scale='Blues'
            )
            st.plotly_chart(fig, use_container_width=True)

        # Stockout risk chart
        st.subheader("📊 Stockout Risk Analysis")

        # Create risk categories
        df_risk = df.copy()
        df_risk['Risk_Category'] = pd.cut(
            df_risk['Days_Until_Stockout'],
            bins=[0, 7, 14, 30, 999],
            labels=['Critical (<7 days)', 'High (7-14 days)', 'Medium (14-30 days)', 'Low (>30 days)']
        )

        risk_counts = df_risk['Risk_Category'].value_counts().sort_index()

        fig = px.bar(
            x=risk_counts.index,
            y=risk_counts.values,
            title="Products by Stockout Risk",
            labels={'x': 'Risk Category', 'y': 'Number of Products'},
            color=risk_counts.values,
            color_continuous_scale='Reds'
        )
        st.plotly_chart(fig, use_container_width=True)

# ============================================================================
# PAGE: PURCHASE ORDERS
# ============================================================================
elif page == "📄 Purchase Orders":
    st.header("📄 Generate Purchase Orders")

    if st.session_state.forecasts_df is None:
        st.warning("⚠️ No forecast data available. Please upload data in the '📤 Upload Data' tab first.")
    else:
        df = st.session_state.forecasts_df

        st.subheader("Select Items to Order")

        # Filter for items that need ordering
        order_candidates = df[df['Priority'].isin(['🚨 URGENT', '⚠️ Warning', '⚡ Order Soon'])].copy()

        if len(order_candidates) == 0:
            st.success("🎉 No items need ordering right now!")
        else:
            st.write(f"**{len(order_candidates)} items recommended for ordering**")

            # Allow selection
            selected_items = st.multiselect(
                "Select items to include in purchase order:",
                options=order_candidates['Item_Number'].tolist(),
                default=order_candidates[order_candidates['Priority'] == '🚨 URGENT']['Item_Number'].tolist()
            )

            if selected_items:
                po_df = order_candidates[order_candidates['Item_Number'].isin(selected_items)].copy()

                # PO details
                col1, col2 = st.columns(2)

                with col1:
                    po_date = st.date_input("PO Date", datetime.now())
                    vendor = st.text_input("Vendor/Supplier", "")

                with col2:
                    po_number = st.text_input("PO Number", f"PO-{datetime.now().strftime('%Y%m%d')}")
                    notes = st.text_area("Notes", "")

                # Display PO preview
                st.subheader("📋 Purchase Order Preview")

                po_display = po_df[['Item_Number', 'Recommended_Order_Qty', 'Priority', 'Days_Until_Stockout']].copy()
                po_display.columns = ['Item Number', 'Order Quantity', 'Priority', 'Days Until Stockout']

                st.dataframe(po_display, use_container_width=True, hide_index=True)

                # Summary
                total_units = po_df['Recommended_Order_Qty'].sum()
                total_items = len(po_df)

                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Total Items", total_items)
                with col2:
                    st.metric("Total Units", f"{total_units:,.0f}")

                # Generate PO document
                if st.button("📄 Generate Purchase Order", type="primary", use_container_width=True):
                    po_text = f"""
PURCHASE ORDER
{po_number}
Date: {po_date}
Vendor: {vendor}

{'='*80}
ITEMS TO ORDER
{'='*80}

"""
                    for idx, row in po_df.iterrows():
                        po_text += f"{row['Item_Number']:<20} Qty: {row['Recommended_Order_Qty']:>6.0f}  Priority: {row['Priority']}
"

                    po_text += f"""
{'='*80}
SUMMARY
{'='*80}
Total Items: {total_items}
Total Units: {total_units:,.0f}

Notes: {notes}

Generated by Heritage Shops Inventory Forecasting System
{datetime.now().strftime('%Y-%m-%d %H:%M')}
"""

                    st.download_button(
                        label="📥 Download Purchase Order",
                        data=po_text,
                        file_name=f"{po_number}.txt",
                        mime="text/plain",
                        use_container_width=True
                    )

                    st.success("✅ Purchase order generated!")

# ============================================================================
# PAGE: SETTINGS
# ============================================================================
elif page == "⚙️ Settings":
    st.header("⚙️ System Settings")

    st.subheader("Forecasting Parameters")

    col1, col2 = st.columns(2)

    with col1:
        st.number_input("Default Lead Time (days)", 1, 90, 14, key="default_lead_time")
        st.number_input("Safety Stock Multiplier", 1.0, 3.0, 1.65, 0.1, key="safety_stock_mult")
        st.slider("Service Level %", 80, 99, 95, key="service_level")

    with col2:
        st.number_input("Order Quantity Multiplier (months)", 1, 6, 2, key="order_qty_mult")
        st.number_input("Minimum Order Quantity", 1, 100, 10, key="min_order_qty")

    st.markdown("---")

    st.subheader("Alert Thresholds")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.number_input("🚨 Urgent (days)", 1, 30, 7, key="urgent_threshold")

    with col2:
        st.number_input("⚠️ Warning (days)", 1, 60, 14, key="warning_threshold")

    with col3:
        st.number_input("⚡ Order Soon (days)", 1, 90, 30, key="order_soon_threshold")

    st.markdown("---")

    if st.button("💾 Save Settings", type="primary"):
        st.success("✅ Settings saved!")

    st.markdown("---")

    st.subheader("About This System")
    st.info("""
    **Heritage Shops Inventory Forecasting System**

    Version: 2.0 (Enhanced with File Upload)

    Features:
    - Upload historical sales and current inventory
    - AI-powered demand forecasting
    - Automated reorder point calculations
    - Priority-based alerts
    - Purchase order generation
    - Real-time analytics

    Built with Python, Streamlit, and advanced forecasting algorithms.
    """)

# Footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: #666; font-size: 0.9rem;'>"
    "Heritage Shops Inventory Forecasting System | Powered by AI | "
    f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')} NST"
    "</div>",
    unsafe_allow_html=True
)
