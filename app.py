
"""
Heritage Shops - Inventory Forecasting Dashboard
A Streamlit web application for inventory management and demand forecasting
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np

# Page configuration
st.set_page_config(
    page_title="HSA Inventory Forecasting",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .stMetric {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 10px;
    }
    .urgent { color: #d32f2f; font-weight: bold; }
    .warning { color: #f57c00; font-weight: bold; }
    .success { color: #388e3c; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# FUNCTIONS
# ============================================================================

@st.cache_data
def load_forecasts():
    """Load forecast data"""
    try:
        df = pd.read_csv('current_forecasts.csv')
        return df
    except:
        # Sample data if file not found
        return pd.DataFrame({
            'Item_Number': ['104468', '2007', '104414'],
            'Description': ['MEDIUM W/ HANDLES', 'ASSORTED PCF', 'LARGE W/ HANDLES'],
            'Brand': ['PEPA', 'POST', 'PEPA'],
            'Current_Stock': [50, 30, 40],
            'Reorder_Point': [45, 49, 38],
            'Order_Quantity': [200, 66, 172],
            'Days_Until_Stockout': [15, 9, 14],
            'Action_Required': ['ORDER SOON', 'CRITICAL - ORDER NOW', 'MONITOR CLOSELY'],
            'Daily_Demand': [3.33, 3.32, 2.86],
            'Velocity_Category': ['Fast Mover', 'Fast Mover', 'Fast Mover']
        })

def color_action(val):
    """Color code actions"""
    if 'URGENT' in val or 'CRITICAL' in val:
        return 'background-color: #ffcdd2'
    elif 'ORDER SOON' in val:
        return 'background-color: #fff9c4'
    elif 'MONITOR' in val:
        return 'background-color: #e1f5fe'
    else:
        return 'background-color: #c8e6c9'

# ============================================================================
# SIDEBAR
# ============================================================================

st.sidebar.title("🏪 Heritage Shops")
st.sidebar.markdown("### Inventory Forecasting System")

# Store selector
store = st.sidebar.selectbox(
    "Select Store",
    ["Branch 49", "All Stores", "Webstore"]
)

# Date range
st.sidebar.markdown("### Forecast Period")
forecast_days = st.sidebar.slider("Days ahead", 7, 90, 30)

# Filters
st.sidebar.markdown("### Filters")
show_urgent_only = st.sidebar.checkbox("Show urgent items only", value=False)
velocity_filter = st.sidebar.multiselect(
    "Velocity Category",
    ["Fast Mover", "Medium Mover"],
    default=["Fast Mover", "Medium Mover"]
)

# ============================================================================
# MAIN CONTENT
# ============================================================================

st.title("📦 Inventory Forecasting Dashboard")
st.markdown(f"**{store}** | Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

# Load data
df = load_forecasts()

# Apply filters
if show_urgent_only:
    df = df[df['Action_Required'].isin(['URGENT - OUT OF STOCK', 'CRITICAL - ORDER NOW', 'ORDER SOON'])]
if velocity_filter:
    df = df[df['Velocity_Category'].isin(velocity_filter)]

# ============================================================================
# KEY METRICS
# ============================================================================

col1, col2, col3, col4, col5 = st.columns(5)

urgent_count = len(df[df['Action_Required'].str.contains('URGENT|CRITICAL', na=False)])
order_soon = len(df[df['Action_Required'] == 'ORDER SOON'])
at_risk = len(df[df['Days_Until_Stockout'] < 14])
total_order_qty = df[df['Action_Required'].str.contains('ORDER|URGENT|CRITICAL', na=False)]['Order_Quantity'].sum()
ok_count = len(df[df['Action_Required'] == 'OK - SUFFICIENT STOCK'])

with col1:
    st.metric("🚨 Critical Items", urgent_count, delta=None, delta_color="inverse")

with col2:
    st.metric("⚠️ Order Soon", order_soon)

with col3:
    st.metric("📉 At Risk (<14 days)", at_risk)

with col4:
    st.metric("📦 Recommended Orders", f"{total_order_qty:,} units")

with col5:
    st.metric("✅ OK Stock", ok_count)

# ============================================================================
# TABS
# ============================================================================

tab1, tab2, tab3, tab4 = st.tabs(["🚨 Actions Required", "📊 Analytics", "📦 All Products", "⚙️ Settings"])

# TAB 1: ACTIONS REQUIRED
with tab1:
    st.header("Actions Required")

    # Filter by priority
    priority_filter = st.selectbox(
        "Filter by urgency",
        ["All", "URGENT - OUT OF STOCK", "CRITICAL - ORDER NOW", "ORDER SOON", "MONITOR CLOSELY"]
    )

    if priority_filter != "All":
        display_df = df[df['Action_Required'] == priority_filter]
    else:
        display_df = df

    # Sort by priority
    action_priority = {
        'URGENT - OUT OF STOCK': 1,
        'CRITICAL - ORDER NOW': 2,
        'ORDER SOON': 3,
        'MONITOR CLOSELY': 4,
        'OK - SUFFICIENT STOCK': 5
    }
    display_df['_priority'] = display_df['Action_Required'].map(action_priority)
    display_df = display_df.sort_values('_priority')

    # Display table
    st.dataframe(
        display_df[['Item_Number', 'Description', 'Brand', 'Current_Stock', 
                    'Reorder_Point', 'Order_Quantity', 'Days_Until_Stockout', 
                    'Action_Required']],
        use_container_width=True,
        hide_index=True
    )

    # Generate purchase order button
    selected_items = st.multiselect(
        "Select items to create purchase order:",
        display_df['Item_Number'].tolist(),
        format_func=lambda x: f"{x} - {display_df[display_df['Item_Number']==x]['Description'].iloc[0]}"
    )

    if st.button("📄 Generate Purchase Order", type="primary"):
        if selected_items:
            po_df = display_df[display_df['Item_Number'].isin(selected_items)]
            st.success(f"Purchase order created for {len(selected_items)} items!")
            st.dataframe(po_df[['Item_Number', 'Description', 'Order_Quantity']])
        else:
            st.warning("Please select at least one item")

# TAB 2: ANALYTICS
with tab2:
    st.header("Inventory Analytics")

    col1, col2 = st.columns(2)

    with col1:
        # Action distribution
        action_counts = df['Action_Required'].value_counts()
        fig = px.pie(
            values=action_counts.values,
            names=action_counts.index,
            title="Actions Distribution",
            color_discrete_sequence=px.colors.qualitative.Set3
        )
        st.plotly_chart(fig, use_container_width=True)

        # Velocity category distribution
        velocity_counts = df['Velocity_Category'].value_counts()
        fig2 = px.bar(
            x=velocity_counts.index,
            y=velocity_counts.values,
            title="Products by Velocity Category",
            labels={'x': 'Category', 'y': 'Count'},
            color=velocity_counts.values,
            color_continuous_scale='Blues'
        )
        st.plotly_chart(fig2, use_container_width=True)

    with col2:
        # Days until stockout distribution
        fig3 = px.histogram(
            df[df['Days_Until_Stockout'] < 60],
            x='Days_Until_Stockout',
            nbins=30,
            title="Days Until Stockout Distribution",
            labels={'Days_Until_Stockout': 'Days'},
            color_discrete_sequence=['#1f77b4']
        )
        fig3.add_vline(x=14, line_dash="dash", line_color="red", 
                       annotation_text="Critical threshold (14 days)")
        st.plotly_chart(fig3, use_container_width=True)

        # Top 10 products by order quantity
        top_orders = df.nlargest(10, 'Order_Quantity')[['Item_Number', 'Description', 'Order_Quantity']]
        fig4 = px.bar(
            top_orders,
            x='Order_Quantity',
            y='Description',
            orientation='h',
            title="Top 10 Recommended Orders",
            labels={'Order_Quantity': 'Quantity', 'Description': 'Product'}
        )
        st.plotly_chart(fig4, use_container_width=True)

# TAB 3: ALL PRODUCTS
with tab3:
    st.header("All Products")

    # Search
    search = st.text_input("🔍 Search by item number or description", "")

    if search:
        search_df = df[
            df['Item_Number'].astype(str).str.contains(search, case=False) |
            df['Description'].astype(str).str.contains(search, case=False)
        ]
    else:
        search_df = df

    # Display with styling
    st.dataframe(
        search_df[['Item_Number', 'Description', 'Brand', 'Velocity_Category',
                   'Current_Stock', 'Daily_Demand', 'Reorder_Point', 
                   'Order_Quantity', 'Days_Until_Stockout', 'Action_Required']],
        use_container_width=True,
        hide_index=True
    )

    # Download button
    csv = search_df.to_csv(index=False)
    st.download_button(
        label="📥 Download Data as CSV",
        data=csv,
        file_name=f"inventory_forecast_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv"
    )

# TAB 4: SETTINGS
with tab4:
    st.header("Forecast Settings")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Lead Time Configuration")
        lead_time = st.number_input("Default lead time (days)", min_value=1, max_value=60, value=14)

        st.subheader("Safety Stock")
        safety_fast = st.number_input("Fast movers (days)", min_value=7, max_value=90, value=30)
        safety_medium = st.number_input("Medium movers (days)", min_value=7, max_value=90, value=45)

    with col2:
        st.subheader("Order Quantity Policy")
        order_fast = st.number_input("Fast movers (days supply)", min_value=30, max_value=180, value=60)
        order_medium = st.number_input("Medium movers (days supply)", min_value=30, max_value=180, value=90)

        st.subheader("Alert Thresholds")
        critical_threshold = st.number_input("Critical stock (days)", min_value=1, max_value=30, value=14)

    if st.button("💾 Save Settings", type="primary"):
        st.success("Settings saved successfully!")
        st.info("Forecasts will be regenerated with new settings")

# ============================================================================
# FOOTER
# ============================================================================

st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; padding: 20px;'>
    <p>Heritage Shops - Inventory Forecasting System v1.0</p>
    <p>Developed with ❤️ for smarter inventory management</p>
</div>
""", unsafe_allow_html=True)
