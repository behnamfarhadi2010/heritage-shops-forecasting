
# Heritage Shops Inventory Forecasting System
## Complete Documentation

---

## 📋 PROJECT OVERVIEW

This system provides AI-powered inventory forecasting for Heritage Shops retail locations in Newfoundland & Labrador. It analyzes historical sales data to predict future demand and generate reorder recommendations.

### Key Features
- ✅ Multiple forecasting algorithms
- ✅ Seasonal adjustment for NL tourism patterns
- ✅ Multi-store support
- ✅ Real-time inventory monitoring
- ✅ Automated purchase order generation
- ✅ Web-based dashboard
- ✅ Mobile-friendly interface

---

## 🗂️ PROJECT STRUCTURE

```
inventory-forecasting/
│
├── SalesHistoryReport.csv          # Your 6-year sales history
├── cleaned_sales_data_branch49.csv # Cleaned data
├── priority_products_for_forecasting.csv # Top 177 products
├── current_forecasts.csv           # Latest forecasts
│
├── database_schema.sql             # PostgreSQL database schema
├── advanced_forecasting.py         # Forecasting algorithms
├── app.py                          # Streamlit web dashboard
│
├── requirements.txt                # Python dependencies (create this)
└── README.md                       # This documentation
```

---

## 🚀 GETTING STARTED

### Prerequisites
- Python 3.8 or higher
- PostgreSQL or MySQL database (optional for production)
- Your POS system sales data export capability

### Installation

1. **Clone or create project directory:**
```bash
mkdir heritage-shops-forecasting
cd heritage-shops-forecasting
```

2. **Create virtual environment:**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies:**
```bash
pip install pandas numpy streamlit plotly scikit-learn
```

4. **Set up database (optional for prototype):**
```bash
psql -U your_username -d your_database -f database_schema.sql
```

### Quick Start (Prototype Mode)

1. **Place your sales data:**
   - Put `SalesHistoryReport.csv` in project directory

2. **Run the web app:**
```bash
streamlit run app.py
```

3. **Open browser:**
   - Navigate to `http://localhost:8501`
   - Dashboard will load with sample forecasts

---

## 💾 DATABASE SCHEMA

### Core Tables

#### 1. **products** - Product master data
- Stores all product information
- Links to sales, inventory, and forecasts

#### 2. **stores** - Store locations
- Branch 49, webstore, other locations
- Manages multi-store inventory

#### 3. **sales_history** - Time-series sales data
- **Critical:** Needs monthly/weekly breakdown
- Currently you have 6-year aggregate
- Required format: `(date, store_id, product_id, quantity)`

#### 4. **inventory_levels** - Current stock
- Real-time inventory per store
- Tracks available vs reserved stock
- Updates when sales occur or orders received

#### 5. **forecasts** - AI predictions
- Generated daily/weekly
- Stores predictions per product per store
- Includes confidence scores

#### 6. **reorder_alerts** - Action items
- Auto-generated alerts for low stock
- Prioritized by urgency
- Tracks acknowledgment status

### Database Views

#### v_stock_status
Quick view of current stock + forecasts for all products

#### v_top_sellers
Top selling products in last 90 days

#### v_pending_alerts
All unacknowledged reorder alerts

---

## 🔮 FORECASTING ALGORITHMS

### 1. Simple Moving Average (SMA)
- **Best for:** Stable demand products
- **Method:** Average of last N periods
- **Use case:** Very slow movers with consistent sales

### 2. Weighted Moving Average (WMA)
- **Best for:** Products with slight trends
- **Method:** Recent periods get higher weights
- **Use case:** Medium movers

### 3. Exponential Smoothing
- **Best for:** Responsive to recent changes
- **Method:** Automatic weight adjustment
- **Use case:** Fast movers with some volatility

### 4. Holt's Linear Trend
- **Best for:** Products with clear trends
- **Method:** Separates level and trend components
- **Use case:** Growing or declining products

### 5. Seasonal Adjustment
- **Best for:** Tourism-dependent products
- **Method:** Multiplies base forecast by seasonal factor
- **NL Tourism Patterns:**
  - Peak: June-August (1.3x - 1.6x)
  - Shoulder: May, September (0.9x - 1.2x)
  - Low: October-April (0.4x - 0.8x)

### 6. Ensemble Method (Recommended)
- **Best for:** All products
- **Method:** Combines multiple algorithms
- **Weights adjusted by velocity category**

---

## 📊 HOW TO USE THE SYSTEM

### For Store Managers

#### Daily Routine
1. **Open dashboard**
   - Check "Actions Required" tab
   - Review urgent items (red)

2. **Review alerts**
   - Items with <14 days stock
   - Out of stock items

3. **Create orders**
   - Select products needing reorder
   - Click "Generate Purchase Order"
   - System suggests optimal quantities

#### Weekly Review
1. **Analytics Tab**
   - Check forecast accuracy
   - Review top sellers
   - Identify slow movers

2. **Adjust as needed**
   - Override recommendations if needed
   - Add notes for special circumstances

### For Administrators

#### Initial Setup
1. **Import historical data**
   - Export monthly sales from POS
   - Run data import script
   - Verify data quality

2. **Configure settings**
   - Set lead times per supplier
   - Define safety stock levels
   - Set seasonal factors

3. **Train staff**
   - Demo dashboard features
   - Explain action priorities
   - Review override procedures

#### Ongoing Management
1. **Monitor accuracy**
   - Review forecast vs actual
   - Adjust algorithm weights
   - Fine-tune parameters

2. **System maintenance**
   - Weekly forecast regeneration
   - Monthly accuracy reports
   - Quarterly seasonality review

---

## 🔧 CONFIGURATION

### Forecasting Parameters

**Lead Times (default: 14 days)**
- How long from order to delivery
- Set per supplier in database

**Safety Stock**
- Fast Movers: 30 days
- Medium Movers: 45 days
- Adjustable in Settings tab

**Order Quantities**
- Fast Movers: 60 days supply
- Medium Movers: 90 days supply

### Seasonal Factors

NL tourism patterns built-in:
```python
nl_seasonality = {
    7: 1.6,   # July peak
    8: 1.5,   # August peak
    1: 0.4,   # January low
    2: 0.4    # February low
}
```

Customize for your specific products in `advanced_forecasting.py`

---

## 📈 DATA REQUIREMENTS

### Current Status
✅ You have: 6 years aggregate sales (Feb 2020 - Feb 2026)
❌ You need: Monthly/weekly breakdown

### Required Data Export from POS

**Sales History (time-series):**
```
Date       | Store | Item_Number | Quantity | Revenue
2024-01-01 | 49    | 104468      | 5        | 50.00
2024-01-01 | 49    | 2007        | 12       | 15.00
...
```

**Current Inventory:**
```
Store | Item_Number | Quantity_On_Hand
49    | 104468      | 150
49    | 2007        | 45
```

**Supplier Information:**
```
Supplier_Code | Lead_Time_Days | Min_Order_Value
PEPA         | 14             | 500.00
POST         | 7              | 250.00
```

### How to Export from Your POS
1. Access reports module
2. Select "Sales History Report"
3. Choose date range: 2020-01-01 to present
4. **Important:** Select "Monthly" or "Weekly" grouping
5. Export as CSV
6. Save as `sales_monthly.csv`

---

## 🎯 ROADMAP

### Phase 1: Foundation (Weeks 1-2) ✅ COMPLETE
- [x] Data analysis
- [x] Database schema
- [x] Basic forecasting model
- [x] Web dashboard prototype

### Phase 2: Implementation (Weeks 3-6)
- [ ] Get monthly sales data from POS
- [ ] Import historical data to database
- [ ] Set up PostgreSQL database
- [ ] Configure suppliers and lead times
- [ ] Train forecasting models on actual data
- [ ] Test with Branch 49 managers

### Phase 3: Testing (Weeks 7-10)
- [ ] Pilot with Branch 49 for 1 month
- [ ] Track forecast accuracy
- [ ] Gather user feedback
- [ ] Refine algorithms
- [ ] Document best practices

### Phase 4: Expansion (Weeks 11-16)
- [ ] Roll out to all stores
- [ ] Add webstore integration
- [ ] Develop mobile app
- [ ] Automate purchase orders
- [ ] Add supplier integrations

### Phase 5: Advanced Features (Month 5+)
- [ ] Machine learning models (XGBoost)
- [ ] Image recognition for inventory counts
- [ ] Predictive analytics dashboard
- [ ] Integration with accounting system
- [ ] Customer demand prediction

---

## 🐛 TROUBLESHOOTING

### Common Issues

**"FileNotFoundError: sales data not found"**
- Ensure CSV files are in project directory
- Check file names match exactly
- Verify file permissions

**"Database connection failed"**
- Check PostgreSQL is running
- Verify connection string
- Check firewall settings

**"Forecasts seem inaccurate"**
- Verify you have time-series data (not aggregate)
- Check seasonal factors match your business
- Review lead time settings
- Ensure current inventory is accurate

**"Dashboard won't load"**
- Check Streamlit is installed: `pip install streamlit`
- Verify you're in correct directory
- Try: `streamlit run app.py --server.port 8502`

---

## 📞 SUPPORT

### For Development Questions
- Review code comments in `advanced_forecasting.py`
- Check database schema documentation
- Refer to Streamlit docs: https://docs.streamlit.io

### For Business Questions
- Review this README
- Check forecasting algorithm explanations
- Consult with store managers on lead times

---

## 📝 CHANGELOG

### Version 1.0 (Feb 2026)
- Initial prototype
- 6 years sales data analyzed
- 177 priority products identified
- Database schema designed
- Web dashboard created
- Advanced forecasting algorithms implemented

### Next Version (Planned)
- Monthly sales data integration
- Multi-store support
- Purchase order automation
- Mobile app interface

---

## 🙏 ACKNOWLEDGMENTS

Built with:
- Python & Pandas
- Streamlit
- PostgreSQL
- Plotly

Developed for Heritage Shops, Newfoundland & Labrador

---

## 📄 LICENSE

Internal use only - Heritage Shops proprietary system
# heritage-shops-forecasting
