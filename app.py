import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# --- PAGE CONFIG ---
st.set_page_config(page_title="Retail Sales Intelligence", layout="wide")

# Custom CSS for KPI cards
st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 22px; }
    .insight-box {
        padding: 20px;
        border-radius: 10px;
        margin: 10px 0;
        border-left: 5px solid #007BFF;
        background-color: #f0f2f6;
    }
    </style>
    """, unsafe_allow_html=True)

# --- HELPER FUNCTIONS ---
def generate_sample_data():
    """Generates dummy data if no files are uploaded."""
    stores = pd.DataFrame({
        'store_id': range(1, 11),
        'region': ['North', 'North', 'South', 'South', 'East', 'West', 'Central', 'North', 'South', 'West'],
        'city': ['Delhi', 'Noida', 'Bangalore', 'Chennai', 'Kolkata', 'Mumbai', 'Indore', 'Gurgaon', 'Hyderabad', 'Pune'],
        'store_format': ['Hypermarket', 'Supermarket', 'Express', 'Hypermarket', 'Supermarket'] * 2,
        'store_name': [f"Store {i}" for i in range(1, 11)],
        'product_category': ['Electronics', 'Fashion', 'Grocery', 'Home', 'Beauty'] * 2
    })
    
    sales = []
    dates = pd.date_range(start="2023-12-01", periods=8, freq='W')
    for date in dates:
        for sid in range(1, 11):
            net_sales = 500000 + (sid * 10000)
            sales.append({
                'store_id': sid,
                'week_start_date': date,
                'net_sales': net_sales,
                'sales_target': 600000,
                'transactions': 1200,
                'footfall': 2400,  # Added footfall for conversion rate
                'returns_amount': 15000,
                'discount_amount': 25000,
                'gross_sales': 540000,
                'stockout_instances': 5,
                'inventory_on_hand': 2000,
                'product_category': stores.loc[stores['store_id']==sid, 'product_category'].values[0]
            })
    return pd.DataFrame(sales), stores

# --- SIDEBAR: FILE UPLOADS ---
st.sidebar.header("📁 Data Integration")
sales_file = st.sidebar.file_uploader("Upload Weekly Sales (.xlsx)", type=['xlsx'])
master_file = st.sidebar.file_uploader("Upload Store Master (.xlsx)", type=['xlsx'])

# Define repository file paths (must match exact file names in GitHub)
DEFAULT_SALES_PATH = "retail_weekly_sales.xlsx"
DEFAULT_MASTER_PATH = "store_master.xlsx"

if sales_file and master_file:
    # 1. User uploaded custom files via UI
    sales_df = pd.read_excel(sales_file)
    master_df = pd.read_excel(master_file)
    st.sidebar.success("Custom Excel files uploaded successfully!")

elif os.path.exists(DEFAULT_SALES_PATH) and os.path.exists(DEFAULT_MASTER_PATH):
    # 2. Automatically load real files stored in your GitHub repo
    sales_df = pd.read_excel(DEFAULT_SALES_PATH)
    master_df = pd.read_excel(DEFAULT_MASTER_PATH)
    st.sidebar.success("Loaded default datasets from GitHub repo.")

else:
    # 3. Fallback to generated sample data if files aren't found
    st.sidebar.info("Using synthetic sample data. Upload your files to refresh.")
    sales_df, master_df = generate_sample_data()

# 1. Clean extra whitespace from column headers
sales_df.columns = sales_df.columns.astype(str).str.strip()
master_df.columns = master_df.columns.astype(str).str.strip()

# 2. Safely merge without duplicate column suffixes (_x and _y)
cols_to_use = [col for col in master_df.columns if col not in sales_df.columns or col == 'store_id']
df = pd.merge(sales_df, master_df[cols_to_use], on='store_id', how='left')

# 3. Standardize column aliases (fixes stockouts vs stockout_instances mismatch)
if 'stockouts' in df.columns and 'stockout_instances' not in df.columns:
    df['stockout_instances'] = df['stockouts']
elif 'stockout_instances' in df.columns and 'stockouts' not in df.columns:
    df['stockouts'] = df['stockout_instances']

# 4. Safely parse dates and drop rows with corrupt date strings
df['week_start_date'] = pd.to_datetime(df['week_start_date'], errors='coerce')
df = df.dropna(subset=['week_start_date'])

# 5. Clean and convert all numeric columns to clean floats
numeric_cols = [
    'net_sales', 'sales_target', 'transactions', 'returns_amount', 
    'discount_amount', 'gross_sales', 'stockout_instances', 'stockouts',
    'inventory_on_hand', 'footfall', 'units_sold', 'customer_rating', 'marketing_spend'
]

for col in numeric_cols:
    if col in df.columns:
        cleaned_series = df[col].astype(str).str.replace(r'[^\d.-]', '', regex=True)
        df[col] = pd.to_numeric(cleaned_series, errors='coerce').fillna(0)

# --- SIDEBAR: GLOBAL FILTERS ---
st.sidebar.header("🔍 Global Filters")

min_date = df['week_start_date'].min().date()
max_date = df['week_start_date'].max().date()
selected_dates = st.sidebar.date_input("Date Range", [min_date, max_date])

if isinstance(selected_dates, (list, tuple)) and len(selected_dates) == 2:
    start_date, end_date = selected_dates
else:
    start_date, end_date = min_date, max_date

regions = st.sidebar.multiselect("Region", options=df['region'].unique(), default=df['region'].unique())
cities = st.sidebar.multiselect("City", options=df[df['region'].isin(regions)]['city'].unique(), default=df[df['region'].isin(regions)]['city'].unique())

# [ADDED FEATURE 1]: Store Name Filter
store_options = df[(df['region'].isin(regions)) & (df['city'].isin(cities))]['store_name'].unique()
selected_stores = st.sidebar.multiselect("Store Name", options=store_options, default=store_options)

formats = st.sidebar.multiselect("Store Format", options=df['store_format'].unique(), default=df['store_format'].unique())
categories = st.sidebar.multiselect("Product Category", options=df['product_category'].unique(), default=df['product_category'].unique())

# Filter dataframe
mask = (
    (df['week_start_date'].dt.date >= start_date) & 
    (df['week_start_date'].dt.date <= end_date) &
    (df['region'].isin(regions)) &
    (df['city'].isin(cities)) &
    (df['store_name'].isin(selected_stores)) &  # [ADDED] store_name filtering
    (df['store_format'].isin(formats)) &
    (df['product_category'].isin(categories))
)
filtered_df = df.loc[mask]

if filtered_df.empty:
    st.warning("⚠️ No data matches the selected filters. Please adjust your global filters.")
    st.stop()
    
# --- MAIN DASHBOARD ---
st.title("📊 Retail Sales Intelligence App")

# --- TOP KPI SUMMARY CARDS ---
# [ADDED FEATURE 2]: Expanded to 6 KPI cards including Conversion Rate
kpi1, kpi2, kpi3, kpi4, kpi5, kpi6 = st.columns(6)

total_net_sales = filtered_df['net_sales'].sum()
total_target = filtered_df['sales_target'].sum()
total_txns = filtered_df['transactions'].sum()
total_returns = filtered_df['returns_amount'].sum()
total_discounts = filtered_df['discount_amount'].sum()
total_gross = filtered_df['gross_sales'].sum()

# Conversion Rate calculation
total_footfall = filtered_df['footfall'].sum() if 'footfall' in filtered_df.columns else 0
conversion_rate = (total_txns / total_footfall * 100) if total_footfall > 0 else 0

kpi1.metric("Net Sales", f"₹{(total_net_sales/1e6):.2f}M")
kpi2.metric("Target Ach.", f"{(total_net_sales/max(total_target,1))*100:.1f}%")
kpi3.metric("ATV", f"₹{total_net_sales/max(total_txns,1):.0f}")
kpi4.metric("Return Rate", f"{(total_returns/max(total_net_sales,1))*100:.1f}%")
kpi5.metric("Discount Rate", f"{(total_discounts/max(total_gross,1))*100:.1f}%")
kpi6.metric("Conversion Rate", f"{conversion_rate:.1f}%")

st.divider()

# --- VISUAL ANALYTICS ---
row1_col1, row1_col2 = st.columns([2, 1])

with row1_col1:
    st.subheader("Weekly Trend: Sales vs Target")
    trend_data = filtered_df.groupby('week_start_date')[['net_sales', 'sales_target']].sum().reset_index()
    fig_trend = px.line(trend_data, x='week_start_date', y=['net_sales', 'sales_target'], 
                        color_discrete_map={'net_sales': '#00CC96', 'sales_target': '#EF553B'})
    st.plotly_chart(fig_trend, use_container_width=True)

with row1_col2:
    st.subheader("Regional Performance")
    reg_data = filtered_df.groupby('region')[['net_sales', 'sales_target']].sum().reset_index()
    reg_data['Achievement %'] = (reg_data['net_sales'] / reg_data['sales_target']) * 100
    fig_reg = px.bar(reg_data, x='region', y='net_sales', text=reg_data['Achievement %'].apply(lambda x: f'{x:.0f}%'))
    st.plotly_chart(fig_reg, use_container_width=True)

row2_col1, row2_col2 = st.columns(2)

with row2_col1:
    st.subheader("Category: Sales & Return Rates")
    cat_data = filtered_df.groupby('product_category').agg({'net_sales': 'sum', 'returns_amount': 'sum'}).reset_index()
    cat_data['Return Rate %'] = (cat_data['returns_amount'] / cat_data['net_sales']) * 100
    fig_cat = px.bar(cat_data, y='product_category', x='net_sales', orientation='h', 
                     color='Return Rate %', color_continuous_scale='Reds')
    st.plotly_chart(fig_cat, use_container_width=True)

with row2_col2:
    st.subheader("Stockout Risk vs Inventory")
    fig_stock = px.scatter(filtered_df, x="inventory_on_hand", y="stockout_instances", 
                          size="net_sales", color="store_format", hover_name="store_name")
    st.plotly_chart(fig_stock, use_container_width=True)

st.subheader("Store Leaderboard (Target Achievement %)")
store_perf = filtered_df.groupby('store_name').agg({'net_sales':'sum', 'sales_target':'sum'}).reset_index()
store_perf['Ach_Pct'] = (store_perf['net_sales'] / store_perf['sales_target']) * 100
store_perf = store_perf.sort_values('Ach_Pct', ascending=False)

top_10 = store_perf.head(10)
bottom_5 = store_perf.tail(5)
leaderboard_df = pd.concat([top_10, bottom_5])

fig_lead = px.bar(leaderboard_df, x='Ach_Pct', y='store_name', orientation='h', 
                 color='Ach_Pct', color_continuous_scale='RdYlGn',
                 title="Top 10 & Bottom 5 Stores")
st.plotly_chart(fig_lead, use_container_width=True)

# --- EXECUTIVE SUMMARY & INSIGHTS ---
st.divider()
st.header("💡 Executive Summary & Business Insights")

# Logic for Insights
best_region = reg_data.loc[reg_data['net_sales'].idxmax(), 'region']
worst_region = reg_data.loc[reg_data['net_sales'].idxmin(), 'region']
underperforming_stores = store_perf[store_perf['Ach_Pct'] < 80]['store_name'].tolist()
high_return_cats = cat_data[cat_data['Return Rate %'] > 8]['product_category'].tolist()

col_i1, col_i2, col_i3 = st.columns(3)

with col_i1:
    st.markdown(f"""<div class='insight-box'>
    <strong>Regional Highlights</strong><br>
    🏆 Best: {best_region}<br>
    ⚠️ Worst: {worst_region}
    </div>""", unsafe_allow_html=True)

with col_i2:
    st.markdown(f"""<div class='insight-box'>
    <strong>Critical Stores (<80% Target)</strong><br>
    {", ".join(underperforming_stores[:5]) if underperforming_stores else "None"}
    </div>""", unsafe_allow_html=True)

with col_i3:
    st.markdown(f"""<div class='insight-box'>
    <strong>High Return Risk (>8%)</strong><br>
    {", ".join(high_return_cats) if high_return_cats else "All categories healthy"}
    </div>""", unsafe_allow_html=True)

# --- EXPORT FEATURES ---
st.sidebar.divider()
st.sidebar.header("📤 Export & Share")

csv = filtered_df.to_csv(index=False).encode('utf-8')
st.sidebar.download_button("Download Filtered Data (CSV)", data=csv, file_name="filtered_retail_data.csv", mime='text/csv')

summary_text = f"""
Executive Summary:
- Total Net Sales: INR {total_net_sales/1e6:.2f}M
- Overall Target Achievement: {(total_net_sales/total_target)*100:.1f}%
- Best Region: {best_region}
- High Return Categories: {", ".join(high_return_cats)}
"""
st.sidebar.download_button("Download Summary Notes", data=summary_text, file_name="executive_summary.txt")