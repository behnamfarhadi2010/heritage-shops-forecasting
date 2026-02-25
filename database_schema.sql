
-- ============================================================================
-- HERITAGE SHOPS INVENTORY FORECASTING DATABASE SCHEMA
-- PostgreSQL / MySQL Compatible
-- ============================================================================

-- 1. STORES TABLE
CREATE TABLE stores (
    store_id SERIAL PRIMARY KEY,
    store_code VARCHAR(10) UNIQUE NOT NULL,
    store_name VARCHAR(100) NOT NULL,
    location VARCHAR(200),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Example data for your stores
-- INSERT INTO stores (store_code, store_name, location) VALUES
-- ('49', 'Branch 49', 'Location TBD'),
-- ('WEBSTORE', 'Online Store', 'E-commerce');

-- ============================================================================

-- 2. PRODUCTS TABLE
CREATE TABLE products (
    product_id SERIAL PRIMARY KEY,
    item_number VARCHAR(50) UNIQUE NOT NULL,
    description TEXT,
    brand VARCHAR(100),
    department VARCHAR(50),
    supplier VARCHAR(100),
    description_code VARCHAR(50),
    supplier_category VARCHAR(50),
    cost DECIMAL(10, 2),
    selling_price DECIMAL(10, 2),
    profit_margin DECIMAL(5, 2),
    velocity_category VARCHAR(20), -- Fast Mover, Medium Mover, Slow Mover, Very Slow
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_products_item_number ON products(item_number);
CREATE INDEX idx_products_velocity ON products(velocity_category);
CREATE INDEX idx_products_brand ON products(brand);
CREATE INDEX idx_products_department ON products(department);

-- ============================================================================

-- 3. SALES HISTORY TABLE (Time-series data)
CREATE TABLE sales_history (
    sale_id SERIAL PRIMARY KEY,
    store_id INTEGER REFERENCES stores(store_id),
    product_id INTEGER REFERENCES products(product_id),
    sale_date DATE NOT NULL,
    quantity_sold INTEGER NOT NULL,
    revenue DECIMAL(10, 2),
    cost DECIMAL(10, 2),
    profit DECIMAL(10, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_sales_date ON sales_history(sale_date);
CREATE INDEX idx_sales_store_product ON sales_history(store_id, product_id);
CREATE INDEX idx_sales_product_date ON sales_history(product_id, sale_date);

-- ============================================================================

-- 4. INVENTORY LEVELS TABLE (Current stock)
CREATE TABLE inventory_levels (
    inventory_id SERIAL PRIMARY KEY,
    store_id INTEGER REFERENCES stores(store_id),
    product_id INTEGER REFERENCES products(product_id),
    quantity_on_hand INTEGER NOT NULL DEFAULT 0,
    quantity_reserved INTEGER DEFAULT 0, -- For online orders
    quantity_available INTEGER GENERATED ALWAYS AS (quantity_on_hand - quantity_reserved) STORED,
    last_counted_at TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(store_id, product_id)
);

CREATE INDEX idx_inventory_store_product ON inventory_levels(store_id, product_id);

-- ============================================================================

-- 5. FORECASTS TABLE (AI predictions)
CREATE TABLE forecasts (
    forecast_id SERIAL PRIMARY KEY,
    store_id INTEGER REFERENCES stores(store_id),
    product_id INTEGER REFERENCES products(product_id),
    forecast_date DATE NOT NULL,
    forecast_period VARCHAR(20), -- 'next_week', 'next_month', 'next_quarter'
    predicted_demand INTEGER,
    confidence_score DECIMAL(5, 2), -- 0-100
    reorder_point INTEGER,
    order_quantity INTEGER,
    days_until_stockout INTEGER,
    action_required VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_forecasts_store_product ON forecasts(store_id, product_id);
CREATE INDEX idx_forecasts_date ON forecasts(forecast_date);

-- ============================================================================

-- 6. SUPPLIERS TABLE
CREATE TABLE suppliers (
    supplier_id SERIAL PRIMARY KEY,
    supplier_code VARCHAR(50) UNIQUE NOT NULL,
    supplier_name VARCHAR(200) NOT NULL,
    contact_name VARCHAR(100),
    email VARCHAR(100),
    phone VARCHAR(20),
    lead_time_days INTEGER DEFAULT 14,
    minimum_order_value DECIMAL(10, 2),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================

-- 7. PURCHASE ORDERS TABLE
CREATE TABLE purchase_orders (
    po_id SERIAL PRIMARY KEY,
    po_number VARCHAR(50) UNIQUE NOT NULL,
    supplier_id INTEGER REFERENCES suppliers(supplier_id),
    store_id INTEGER REFERENCES stores(store_id),
    order_date DATE NOT NULL,
    expected_delivery_date DATE,
    status VARCHAR(20), -- 'DRAFT', 'SUBMITTED', 'RECEIVED', 'CANCELLED'
    total_amount DECIMAL(10, 2),
    notes TEXT,
    created_by VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================

-- 8. PURCHASE ORDER ITEMS TABLE
CREATE TABLE purchase_order_items (
    po_item_id SERIAL PRIMARY KEY,
    po_id INTEGER REFERENCES purchase_orders(po_id),
    product_id INTEGER REFERENCES products(product_id),
    quantity_ordered INTEGER NOT NULL,
    quantity_received INTEGER DEFAULT 0,
    unit_cost DECIMAL(10, 2),
    total_cost DECIMAL(10, 2) GENERATED ALWAYS AS (quantity_ordered * unit_cost) STORED,
    notes TEXT
);

-- ============================================================================

-- 9. REORDER ALERTS TABLE
CREATE TABLE reorder_alerts (
    alert_id SERIAL PRIMARY KEY,
    store_id INTEGER REFERENCES stores(store_id),
    product_id INTEGER REFERENCES products(product_id),
    alert_type VARCHAR(20), -- 'LOW_STOCK', 'OUT_OF_STOCK', 'OVERSTOCK'
    current_stock INTEGER,
    recommended_order_qty INTEGER,
    priority INTEGER, -- 1 = Critical, 5 = Low
    is_acknowledged BOOLEAN DEFAULT FALSE,
    acknowledged_by VARCHAR(100),
    acknowledged_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_alerts_unacknowledged ON reorder_alerts(is_acknowledged, priority);

-- ============================================================================

-- 10. FORECAST ACCURACY TRACKING
CREATE TABLE forecast_accuracy (
    accuracy_id SERIAL PRIMARY KEY,
    forecast_id INTEGER REFERENCES forecasts(forecast_id),
    actual_demand INTEGER,
    predicted_demand INTEGER,
    accuracy_percentage DECIMAL(5, 2),
    absolute_error INTEGER GENERATED ALWAYS AS (ABS(actual_demand - predicted_demand)) STORED,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================

-- USEFUL VIEWS

-- Current Stock Status with Forecasts
CREATE VIEW v_stock_status AS
SELECT 
    s.store_code,
    s.store_name,
    p.item_number,
    p.description,
    p.brand,
    p.velocity_category,
    i.quantity_available as current_stock,
    f.predicted_demand,
    f.reorder_point,
    f.order_quantity,
    f.days_until_stockout,
    f.action_required
FROM inventory_levels i
JOIN stores s ON i.store_id = s.store_id
JOIN products p ON i.product_id = p.product_id
LEFT JOIN LATERAL (
    SELECT * FROM forecasts f2
    WHERE f2.store_id = i.store_id 
    AND f2.product_id = i.product_id
    ORDER BY f2.created_at DESC
    LIMIT 1
) f ON true;

-- Top Sellers by Store
CREATE VIEW v_top_sellers AS
SELECT 
    s.store_code,
    p.item_number,
    p.description,
    p.brand,
    SUM(sh.quantity_sold) as total_sold,
    SUM(sh.revenue) as total_revenue,
    SUM(sh.profit) as total_profit
FROM sales_history sh
JOIN stores s ON sh.store_id = s.store_id
JOIN products p ON sh.product_id = p.product_id
WHERE sh.sale_date >= CURRENT_DATE - INTERVAL '90 days'
GROUP BY s.store_code, p.item_number, p.description, p.brand
ORDER BY total_sold DESC;

-- Pending Reorder Alerts
CREATE VIEW v_pending_alerts AS
SELECT 
    s.store_name,
    p.item_number,
    p.description,
    a.alert_type,
    a.current_stock,
    a.recommended_order_qty,
    a.priority,
    a.created_at
FROM reorder_alerts a
JOIN stores s ON a.store_id = s.store_id
JOIN products p ON a.product_id = p.product_id
WHERE a.is_acknowledged = FALSE
ORDER BY a.priority ASC, a.created_at ASC;
