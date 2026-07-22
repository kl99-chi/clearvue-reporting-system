import calendar
import datetime
import io
import base64
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, dcc, html, dash_table, Input, Output, State
from dash.exceptions import PreventUpdate
from dash.dcc import Download
from dash.dcc.express import send_data_frame
from pymongo import MongoClient
import certifi
import os

# ---------- CONFIG ----------
MONGO_URI = os.environ.get(
    "MONGO_URI"
)
DB_NAME = os.environ.get("DB_NAME")

COL_SALES = "Sales_Header"
COL_LINES = "Sales_Lines"
COL_PRODUCTS = "Products"
COL_BRANDS = "Product_Brands"
COL_CATEGORIES = "Product_Categories"
COL_CUSTOMERS = "Customers"
COL_AGE = "Age_Analysis"
COL_SUPPLIERS = "Suppliers"

# ---------- THEME ----------
BACKGROUND = "#0e1117"
CARD_BG = "#161a25"
BORDER = "#2a2f3a"
TEXT = "#e6e6e6"
ACCENT = "#00d1b2"

graph_card_style = {
    "border": f"1px solid {BORDER}",
    "borderRadius": "12px",
    "padding": "6px",
    "backgroundColor": CARD_BG,
    "margin": "16px 0",
    "boxShadow": "0 2px 10px rgba(0,0,0,0.35)"
}

tab_style = {
    "backgroundColor": "#1e2130",
    "color": "#a0a8b8",
    "padding": "10px 18px",
    "border": f"1px solid {BORDER}",
    "borderBottom": "none",
    "borderRadius": "10px 10px 0 0",
    "marginRight": "6px",
    "fontWeight": "500",
}
tab_selected_style = {
    "backgroundColor": "#2b2f3a",
    "color": "#ffffff",
    "padding": "10px 18px",
    "border": f"1px solid {ACCENT}",
    "borderBottom": f"2px solid {ACCENT}",
    "boxShadow": "0 -2px 8px rgba(0,0,0,0.3)"
}

TABLE_STYLE = {
    "style_table": {
        "overflowX": "auto",
        "border": f"1px solid {BORDER}",
        "borderRadius": "12px",
        "backgroundColor": CARD_BG,
        "margin": "16px 0",
        "boxShadow": "0 2px 10px rgba(0,0,0,0.35)"
    },
    "style_header": {"backgroundColor": "#1f2630","color": TEXT,"fontWeight": "600","border": f"1px solid {BORDER}"},
    "style_cell": {"backgroundColor": CARD_BG,"color": TEXT,"border": f"1px solid {BORDER}","fontSize": "14px"},
    "style_filter": {"backgroundColor": "#1c2230","color": TEXT,"border": f"1px solid {BORDER}"},
    "style_data": {"backgroundColor": CARD_BG,"color": TEXT,"border": f"1px solid {BORDER}"},
    "style_data_conditional": [{"if": {"state": "selected"}, "backgroundColor": "#284b63", "color": "#fff"}],
}

# ---------- FUNCTIONS ----------
def apply_dark_theme(fig):
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor=CARD_BG,
        plot_bgcolor=CARD_BG,
        font=dict(color=TEXT),
        title=dict(font=dict(color=TEXT)),
        legend=dict(bgcolor=CARD_BG, bordercolor=BORDER, borderwidth=1),
        margin=dict(l=40,r=40,t=60,b=40),
        hovermode="x unified",
    )
    fig.update_xaxes(showgrid=True,gridcolor=BORDER,zeroline=False,linecolor="#3b3b3b",ticks="outside")
    fig.update_yaxes(showgrid=True,gridcolor=BORDER,zeroline=False,linecolor="#3b3b3b",ticks="outside")
    return fig

def safe_load(col_name):
    if db is not None:
        try:
            return pd.DataFrame(list(db[col_name].find()))
        except Exception as e:
            print(f"⚠️ Failed to load {col_name}: {e}")
    return pd.DataFrame()

def normalize_columns(df):
    df.columns = [str(c).strip().upper() for c in df.columns]
    return df

def oid_to_str(x):
    try: return str(x)
    except Exception: return x.get("$oid") if hasattr(x,"get") else None

def last_weekday_of_month(year:int,month:int,weekday:int)->datetime.date:
    last_day = calendar.monthrange(year,month)[1]
    d = datetime.date(year,month,last_day)
    while d.weekday()!=weekday:
        d -= datetime.timedelta(days=1)
    return d

def get_financial_period_for_date(dt):
    if pd.isna(dt): return None,None,None
    if isinstance(dt,(pd.Timestamp,datetime.datetime)): dt=dt.date()
    for offset in (-1,0,1):
        c_month,c_year=dt.month+offset,dt.year
        while c_month<1: c_month+=12;c_year-=1
        while c_month>12: c_month-=12;c_year+=1
        p_month,p_year=c_month-1,c_year
        if p_month<1:p_month=12;p_year-=1
        start=last_weekday_of_month(p_year,p_month,5)
        end=last_weekday_of_month(c_year,c_month,4)
        if start<=dt<=end:return f"{c_year}-{c_month:02d}",start,end
    fallback_label=f"{dt.year}-{dt.month:02d}"
    start=last_weekday_of_month(dt.year if dt.month>1 else dt.year-1, dt.month-1 if dt.month>1 else 12,5)
    end=last_weekday_of_month(dt.year,dt.month,4)
    return fallback_label,start,end

# ---------- MONGO CONNECTION ----------
client = None
db = None
try:
    client = MongoClient(MONGO_URI, tlsCAFile=certifi.where(), serverSelectionTimeoutMS=15000, connectTimeoutMS=10000)
    db = client[DB_NAME]
    client.admin.command("ping")
    print("✅ Connected to MongoDB Atlas successfully")
except Exception as e:
    print("⚠️ MongoDB Atlas connection failed:", e)
    client = None
    db = None

# ---------- LOAD DATA ----------
brands = safe_load(COL_BRANDS)
categories = safe_load(COL_CATEGORIES)
products = safe_load(COL_PRODUCTS)
sales_hdr = safe_load(COL_SALES)
sale_lines_df = safe_load(COL_LINES)
customers = safe_load(COL_CUSTOMERS)
age_analysis = safe_load(COL_AGE)
suppliers = safe_load(COL_SUPPLIERS)

for df_name in ['brands','categories','products','sales_hdr','sale_lines_df','customers','age_analysis','suppliers']:
    locals()[df_name] = normalize_columns(locals()[df_name])

for df in [brands,categories,products,sales_hdr,sale_lines_df,customers,age_analysis,suppliers]:
    if "_ID" in df.columns:
        df["_ID"] = df["_ID"].apply(oid_to_str)

# ---------- FALLBACK DUMMY DATA IF EMPTY ----------
if sale_lines_df.empty:
    sale_lines_df = pd.DataFrame({
        'DOC_NUMBER': ['INV001', 'INV001', 'INV002', 'INV002', 'INV003'],
        'INVENTORY_CODE': ['PROD1', 'PROD2', 'PROD1', 'PROD3', 'PROD2'],
        'QUANTITY': [10, 5, 8, 12, 7],
        'UNIT_SELL_PRICE': [100, 200, 100, 150, 200]
    })

if sales_hdr.empty:
    sales_hdr = pd.DataFrame({
        'DOC_NUMBER': ['INV001', 'INV002', 'INV003'],
        'TRANS_DATE': ['2023-01-01', '2023-01-02', '2023-01-03'],
        'CUSTOMER_NUMBER': ['CUST1', 'CUST2', 'CUST3'],
        'TRANSTYPE_CODE': ['SALE', 'RETURN', 'SALE']
    })

if customers.empty:
    customers = pd.DataFrame({
        'CUSTOMER_NUMBER': ['CUST1', 'CUST2', 'CUST3'],
        'REGION_CODE': ['North', 'South', 'East'],
        'CREDIT_LIMIT': [5000, 3000, 4000]
    })

if products.empty:
    products = pd.DataFrame({
        'INVENTORY_CODE': ['PROD1', 'PROD2', 'PROD3'],
        'PRODUCT_DESC': ['Product A', 'Product B', 'Product C'],
        'BRAND_DESC': ['Brand X', 'Brand Y', 'Brand X']
    })

if suppliers.empty:
    suppliers = pd.DataFrame({
        'SUPPLIER_DESC': ['Supplier A', 'Supplier B', 'Supplier C'],
        'CREDIT_LIMIT': [10000, 8000, 6000],
        'EXCLSV': ['Y', 'N', 'Y']
    })

if age_analysis.empty:
    age_analysis = pd.DataFrame({
        'FIN_PERIOD': ['2023-01', '2023-02'],
        'TOTAL_DUE': [1000, 1200],
        'AMT_CURRENT': [800, 900],
        'AMT_30_DAYS': [100, 150],
        'AMT_60_DAYS': [50, 100],
        'AMT_90_DAYS': [50, 50]
    })

# ---------- MERGE SALES LINES WITH HEADER ----------
required_cols = ["DOC_NUMBER","TRANS_DATE","CUSTOMER_NUMBER"]
sale_lines_df = sale_lines_df.merge(sales_hdr[required_cols], on="DOC_NUMBER", how="left")
sale_lines_df["TRANS_DATE"] = pd.to_datetime(sale_lines_df["TRANS_DATE"], errors="coerce")
hdr_dates = pd.to_datetime(sales_hdr["TRANS_DATE"], errors="coerce")

# ---------- COMPUTE TOTALS ----------
if "QUANTITY" in sale_lines_df.columns:
    sale_lines_df["QUANTITY"] = pd.to_numeric(sale_lines_df["QUANTITY"], errors="coerce").fillna(0)
else:
    sale_lines_df["QUANTITY"] = 0
if "UNIT_SELL_PRICE" in sale_lines_df.columns:
    sale_lines_df["UNIT_SELL_PRICE"] = pd.to_numeric(sale_lines_df["UNIT_SELL_PRICE"], errors="coerce").fillna(0)
else:
    sale_lines_df["UNIT_SELL_PRICE"] = 0
sale_lines_df["LINE_TOTAL"] = sale_lines_df["QUANTITY"] * sale_lines_df["UNIT_SELL_PRICE"]
sale_lines_df["FINANCIAL_PERIOD"] = sale_lines_df["TRANS_DATE"].apply(lambda ts: get_financial_period_for_date(ts)[0] or "Unknown")

# ---------- INITIAL SALES DATA ----------
period_col = sale_lines_df['TRANS_DATE'].dt.date.astype(str)
sales_agg = sale_lines_df.assign(PERIOD=period_col).groupby("PERIOD", as_index=False).agg(total_sales=pd.NamedAgg("LINE_TOTAL","sum")).sort_values("PERIOD")
initial_sales_data = [{k: v for k, v in row.items()} for row in sales_agg.to_dict("records")]
initial_sales_columns = [{"name": str(i), "id": str(i)} for i in sales_agg.columns]
initial_sales_fig = px.line(sales_agg, x="PERIOD", y="total_sales", markers=True, title="Daily Sales Trend")
initial_sales_fig = apply_dark_theme(initial_sales_fig)

# ---------- DATE RANGE ----------
min_date = sale_lines_df['TRANS_DATE'].min().date() if not sale_lines_df.empty else pd.Timestamp('2020-01-01').date()
max_date = sale_lines_df['TRANS_DATE'].max().date() if not sale_lines_df.empty else pd.Timestamp('2023-12-31').date()

# ---------- CUSTOMER SALES ----------
cust_sales = sale_lines_df.groupby("CUSTOMER_NUMBER", as_index=False).agg(
    total_sales=pd.NamedAgg("LINE_TOTAL","sum"),
    total_qty=pd.NamedAgg("QUANTITY","sum")
)
cust_sales = cust_sales.merge(customers[["CUSTOMER_NUMBER","REGION_CODE","CREDIT_LIMIT"]],on="CUSTOMER_NUMBER",how="left")
cust_sales_fig = px.bar(cust_sales.sort_values("total_sales",ascending=False).head(20),
                        x="CUSTOMER_NUMBER",y="total_sales",color="REGION_CODE",
                        title="Top 20 Customers by Sales")
cust_sales_fig = apply_dark_theme(cust_sales_fig)

# ---------- AGE ANALYSIS ----------
if not age_analysis.empty:
    numeric_cols = [c for c in age_analysis.columns if c not in ["_ID","CUSTOMER_NUMBER","FIN_PERIOD"]]
    for c in numeric_cols: age_analysis[c]=pd.to_numeric(age_analysis[c],errors="coerce").fillna(0)
    age_summary = age_analysis.groupby("FIN_PERIOD",as_index=False).agg(
        total_due=pd.NamedAgg("TOTAL_DUE","sum"),
        current=pd.NamedAgg("AMT_CURRENT","sum"),
        over_30=pd.NamedAgg("AMT_30_DAYS","sum"),
        over_60=pd.NamedAgg("AMT_60_DAYS","sum"),
        over_90=pd.NamedAgg("AMT_90_DAYS","sum")
    )
    age_fig = px.area(age_summary,x="FIN_PERIOD",y=["current","over_30","over_60","over_90"],title="Age Analysis by Period")
else:
    age_summary = pd.DataFrame()
    age_fig = go.Figure().add_annotation(text="No Age Analysis data found",showarrow=False)
age_fig = apply_dark_theme(age_fig)

# ---------- TRANSACTIONS ----------
trans_summary = sales_hdr.assign(FINANCIAL_PERIOD=hdr_dates.dt.to_period("M").astype(str))
trans_summary = trans_summary.groupby("FINANCIAL_PERIOD", as_index=False).size().rename(columns={"size":"TRANSACTION_COUNT"})
trans_fig = px.line(trans_summary,x="FINANCIAL_PERIOD",y="TRANSACTION_COUNT",markers=True,title="Transactions per Month")
trans_fig = apply_dark_theme(trans_fig)

# ---------- SUPPLIER SPEND ----------
supplier_fig = px.bar(suppliers.sort_values("CREDIT_LIMIT",ascending=False),
                      x="SUPPLIER_DESC",y="CREDIT_LIMIT",title="Suppliers by Credit Limit") \
               if not suppliers.empty else go.Figure().add_annotation(text="No Supplier data",showarrow=False)
supplier_fig = apply_dark_theme(supplier_fig)

# ---------- PRODUCT REPORT ----------
if not products.empty:
    for col in ["BRAND_CODE_Y","PRODBRA_CODE","PRODBRA_DESC"]:
        if col in products.columns:
            products.drop(columns=[col], inplace=True)
    products_full = products.copy()
    prod_sales = sale_lines_df.groupby("INVENTORY_CODE", as_index=False).agg(
        total_sales=pd.NamedAgg("LINE_TOTAL","sum"),
        total_qty=pd.NamedAgg("QUANTITY","sum")
    )
    prod_sales = prod_sales.merge(products_full,on="INVENTORY_CODE",how="left")
    prod_x_col="PRODUCT_DESC" if "PRODUCT_DESC" in prod_sales.columns else "INVENTORY_CODE"
    prod_color_col="BRAND_DESC" if "BRAND_DESC" in prod_sales.columns else None
    prod_sales_fig = px.bar(prod_sales.sort_values("total_sales",ascending=False).head(20),
                            x=prod_x_col,y="total_sales",color=prod_color_col,
                            title="Top 20 Products by Sales")
else:
    prod_sales=pd.DataFrame()
    prod_sales_fig = go.Figure().add_annotation(text="No Product data",showarrow=False)
prod_sales_fig = apply_dark_theme(prod_sales_fig)

prod_cat_col = 'PRODCAT' if 'PRODCAT' in prod_sales.columns else ('PROD_CAT' if 'PROD_CAT' in prod_sales.columns else None)
prod_cat_code_col = 'PRODCAT_CODE' if 'PRODCAT_CODE' in prod_sales.columns else None

# ---------- DASH APP ----------
app = Dash(__name__)
app.title="ClearVue Integrated Dashboard"

app.layout = html.Div([
    html.H1("📊 ClearVue Integrated Business Dashboard",style={"textAlign":"center","color":TEXT}),
    #dcc.Interval(id="interval-component", interval=15*1000, n_intervals=0),  # refresh every 15s
    dcc.Tabs([

        # ---------- MAKE BI METRICS THE FIRST (LAUNCH) TAB ----------
        dcc.Tab(label="📈 BI Metrics (Managers)", style=tab_style, selected_style=tab_selected_style, children=[
            html.H2("Executive KPIs and Business Metrics", style={"color": TEXT, "textAlign": "center", "marginTop": "20px"}),

            # KPI Section
            html.Div([
                html.Div([
                    html.H4("Gross Revenue", style={"color": TEXT}),
                    html.H3(f"R{sale_lines_df['LINE_TOTAL'].sum():,.2f}", style={"color": ACCENT})
                ], style={"width": "18%", "display": "inline-block", "textAlign": "center", "backgroundColor": CARD_BG, "borderRadius": "12px", "padding": "15px", "margin": "8px"}),

                html.Div([
                    html.H4("Avg Order Value (AOV)", style={"color": TEXT}),
                    html.H3(f"R{sale_lines_df['LINE_TOTAL'].sum() / max(len(sales_hdr),1):,.2f}", style={"color": ACCENT})
                ], style={"width": "18%", "display": "inline-block", "textAlign": "center", "backgroundColor": CARD_BG, "borderRadius": "12px", "padding": "15px", "margin": "8px"}),

                html.Div([
                    html.H4("Monthly Growth Rate", style={"color": TEXT}),
                    html.H3(f"{( (sale_lines_df.groupby(sale_lines_df['TRANS_DATE'].dt.to_period('M'))['LINE_TOTAL'].sum().pct_change().fillna(0).iloc[-1]) * 100):.2f}%", style={"color": ACCENT})
                ], style={"width": "18%", "display": "inline-block", "textAlign": "center", "backgroundColor": CARD_BG, "borderRadius": "12px", "padding": "15px", "margin": "8px"}),

                html.Div([
                    html.H4("Top Region", style={"color": TEXT}),
                    html.H3(f"{cust_sales.groupby('REGION_CODE')['total_sales'].sum().idxmax() if not cust_sales.empty else 'N/A'}", style={"color": ACCENT})
                ], style={"width": "18%", "display": "inline-block", "textAlign": "center", "backgroundColor": CARD_BG, "borderRadius": "12px", "padding": "15px", "margin": "8px"}),

                html.Div([
                    html.H4("Top 5 Cust. % of Sales", style={"color": TEXT}),
                    html.H3(f"{(cust_sales.sort_values('total_sales',ascending=False).head(5)['total_sales'].sum() / max(cust_sales['total_sales'].sum(),1) * 100):.1f}%", style={"color": ACCENT})
                ], style={"width": "18%", "display": "inline-block", "textAlign": "center", "backgroundColor": CARD_BG, "borderRadius": "12px", "padding": "15px", "margin": "8px"}),
            ], style={"textAlign": "center"}),

            # KPI Graphs
            html.H3("Revenue and Growth Trend", style={"color": TEXT, "marginTop": "40px"}),
            dcc.Graph(
                figure=apply_dark_theme(
                    px.line(
                        sale_lines_df.assign(Month=sale_lines_df['TRANS_DATE'].dt.to_period('M').astype(str))
                        .groupby("Month", as_index=False)["LINE_TOTAL"].sum(),
                        x="Month",
                        y="LINE_TOTAL",
                        title="Monthly Revenue Trend"
                    )
                ),
                style=graph_card_style
            ),

            html.H3("Sales by Region", style={"color": TEXT, "marginTop": "30px"}),
            dcc.Graph(
                figure=apply_dark_theme(
                    px.pie(
                        sale_lines_df.merge(customers[["CUSTOMER_NUMBER","REGION_CODE"]], on="CUSTOMER_NUMBER", how="left")
                        .groupby("REGION_CODE", as_index=False)["LINE_TOTAL"].sum(),
                        names="REGION_CODE",
                        values="LINE_TOTAL",
                        title="Sales Distribution by Region"
                    )
                ),
                style=graph_card_style
            ),

            html.Button("Download KPI Summary", id="bi_btn"),
            Download(id="bi_download")
        ]),

        dcc.Tab(label="💰 Sales Overview",style=tab_style,selected_style=tab_selected_style,children=[
            # KPI cards (dynamic placeholders)
            html.Div(id="sales-kpi-cards", children=[
                html.Div([
                    html.Div(id="sales_kpi_total", children=[
                        html.H4("Total Revenue", style={"color": TEXT}),
                        html.H3(f"R{sale_lines_df['LINE_TOTAL'].sum():,.2f}", style={"color": ACCENT})
                    ], style={"width": "18%", "display": "inline-block", "textAlign": "center", "backgroundColor": CARD_BG, "borderRadius": "12px", "padding": "15px", "margin": "8px"})
                ], style={"textAlign": "center"})
            ], style={"marginTop":"8px"}),

            dcc.Dropdown(
                id='sales-group-by',
                options=[
                    {'label': 'Daily', 'value': 'D'},
                    {'label': 'Weekly', 'value': 'W'},
                    {'label': 'Monthly', 'value': 'M'},
                    {'label': 'Quarterly', 'value': 'Q'},
                    {'label': 'Annual', 'value': 'A'}
                ],
                value='D',
                style={'width': '300px', 'margin': '10px', 'backgroundColor': CARD_BG, 'color': 'black', 'border': f'1px solid {BORDER}', 'option': {'color': 'black', 'backgroundColor': 'white'}}
            ),
            dcc.DatePickerRange(
                id='sales-date-range',
                start_date=str(min_date),
                end_date=str(max_date),
                min_date_allowed=str(min_date),
                max_date_allowed=str(max_date),
                style={'margin': '10px'}
            ),
            dcc.Graph(id='sales-graph', style=graph_card_style),
            dash_table.DataTable(id='sales-table', columns=[{"name": str(i), "id": str(i)} for i in sales_agg.columns],
                                 data=[{str(k): v for k, v in row.items()} for row in sales_agg.to_dict("records")],
                                 page_size=20,sort_action="native",filter_action="native",**TABLE_STYLE),
            html.Button("Download Excel", id="sales_btn"),
            Download(id="sales_download")
        ]),

        dcc.Tab(label="🧾 Customer Report",style=tab_style,selected_style=tab_selected_style,children=[
            dcc.Dropdown(
                id='cust-region-filter',
                options=[{'label': r, 'value': r} for r in sorted(cust_sales['REGION_CODE'].dropna().unique())],
                value=[],
                placeholder="Filter by Region Code",
                multi=True,
                style={'width': '300px', 'margin': '10px', 'backgroundColor': CARD_BG, 'color': 'black', 'border': f'1px solid {BORDER}', 'option': {'color': 'black', 'backgroundColor': 'white'}}
            ),
            dcc.Graph(id='cust-graph', figure=cust_sales_fig,style=graph_card_style),
            dash_table.DataTable(id='cust-table', columns=[{"name":str(i),"id":str(i)} for i in cust_sales.columns],
                                 data=[{str(k): v for k, v in row.items()} for row in cust_sales.to_dict("records")],
                                 page_size=20,sort_action="native",filter_action="native",**TABLE_STYLE),
            html.Button("Download Excel", id="cust_btn"),
            Download(id="cust_download")
        ]),

        dcc.Tab(label="📅 Age Analysis",style=tab_style,selected_style=tab_selected_style,children=[
            dcc.Graph(figure=age_fig,style=graph_card_style),
            dash_table.DataTable(columns=[{"name":str(i),"id":str(i)} for i in age_summary.columns],
                                 data=[{str(k): v for k, v in row.items()} for row in age_summary.to_dict("records")],
                                 page_size=20,sort_action="native",filter_action="native",**TABLE_STYLE),
            html.Button("Download Excel", id="age_btn"),
            Download(id="age_download")
        ]),

        dcc.Tab(label="🔁 Transactions",style=tab_style,selected_style=tab_selected_style,children=[
            dcc.Dropdown(
                id='trans-type-filter',
                options=[{'label': t, 'value': t} for t in sorted(sales_hdr['TRANSTYPE_CODE'].dropna().unique())],
                value=[],
                placeholder="Filter by Transaction Type Code",
                multi=True,
                style={'width': '300px', 'margin': '10px', 'backgroundColor': CARD_BG, 'color': 'black', 'border': f'1px solid {BORDER}', 'option': {'color': 'black', 'backgroundColor': 'white'}}
            ),
            dcc.Graph(id='trans-graph', style=graph_card_style),
            dash_table.DataTable(id='trans-table', columns=[{"name":str(i),"id":str(i)} for i in sales_hdr.columns],
                                 data=[{str(k): v for k, v in row.items()} for row in sales_hdr.to_dict("records")],
                                 page_size=20,sort_action="native",filter_action="native",**TABLE_STYLE),
            html.Button("Download Excel", id="trans_btn"),
            Download(id="trans_download")
        ]),

        dcc.Tab(label="🏭 Supplier Report",style=tab_style,selected_style=tab_selected_style,children=[
            dcc.Dropdown(
                id='sup-filter',
                options=[{'label': e, 'value': e} for e in sorted(suppliers['EXCLSV'].dropna().unique())],
                value=[],
                placeholder="Filter by EXCLSV code",
                multi=True,
                style={'width': '300px', 'margin': '10px', 'backgroundColor': CARD_BG, 'color': 'black', 'border': f'1px solid {BORDER}', 'option': {'color': 'black', 'backgroundColor': 'white'}}
            ),
            dcc.DatePickerRange(
                id='sup-date-range',
                start_date=str(min_date),
                end_date=str(max_date),
                min_date_allowed=str(min_date),
                max_date_allowed=str(max_date),
                style={'margin': '10px'}
            ),
            dcc.Graph(id='sup-graph', style=graph_card_style),
            dash_table.DataTable(id='sup-table', columns=[{"name":str(i),"id":str(i)} for i in suppliers.columns],
                                 data=[{str(k): v for k, v in row.items()} for row in suppliers.to_dict("records")],
                                 page_size=20,sort_action="native",filter_action="native",**TABLE_STYLE),
            html.Button("Download Excel", id="sup_btn"),
            Download(id="sup_download")
        ]),

        dcc.Tab(label="🛒 Product Report",style=tab_style,selected_style=tab_selected_style,children=[
            dcc.Graph(id='prod-graph', figure=prod_sales_fig,style=graph_card_style),
            dash_table.DataTable(id='prod-table', columns=[{"name":str(i),"id":str(i)} for i in prod_sales.columns],
                                 data=[{str(k): v for k, v in row.items()} for row in prod_sales.to_dict("records")],
                                 page_size=20,sort_action="native",filter_action="native",**TABLE_STYLE),
            html.Button("Download Excel", id="prod_btn"),
            Download(id="prod_download")
        ]),

        dcc.Tab(label="📊 Key Insights", style=tab_style, selected_style=tab_selected_style, children=[
            # Monthly Sales by Region
            html.H3("Monthly Sales by Region", style={"color": TEXT, "marginTop": "10px"}),
            # Aggregate sales by region and financial period
            dcc.Graph(
                figure=apply_dark_theme(
                    px.bar(
                        sale_lines_df.merge(customers[["CUSTOMER_NUMBER","REGION_CODE"]], on="CUSTOMER_NUMBER", how="left")
                        .groupby(["FINANCIAL_PERIOD","REGION_CODE"], as_index=False)["LINE_TOTAL"].sum(),
                        x="FINANCIAL_PERIOD",
                        y="LINE_TOTAL",
                        color="REGION_CODE",
                        title="Monthly Sales by Region"
                    )
                ),
                style=graph_card_style
            ),
            html.Button("Download Excel", id="insights_sales_btn"),
            Download(id="insights_sales_download"),

            # Top Suppliers
            html.H3("Top Suppliers by Credit Limit", style={"color": TEXT, "marginTop": "30px"}),
            dcc.Graph(
                figure=apply_dark_theme(
                    px.bar(
                        suppliers.sort_values("CREDIT_LIMIT", ascending=False).head(20),
                        x="SUPPLIER_DESC",
                        y="CREDIT_LIMIT",
                        title="Top 20 Suppliers"
                    )
                ),
                style=graph_card_style
            ),
            html.Button("Download Excel", id="insights_sup_btn"),
            Download(id="insights_sup_download"),

            # Top Products
            html.H3("Top Products by Sales", style={"color": TEXT, "marginTop": "30px"}),
            dcc.Graph(
                figure=prod_sales_fig,
                style=graph_card_style
            ),
            html.Button("Download Excel", id="insights_prod_btn"),
            Download(id="insights_prod_download"),
        ])

    ])
],style={"backgroundColor":BACKGROUND,"padding":"20px"})

# ---------- UPDATE CALLBACKS ----------
@app.callback(
    Output('sales-graph', 'figure'),
    Output('sales-table', 'columns'),
    Output('sales-table', 'data'),
    Output('sales-kpi-cards', 'children'),
    Input('sales-group-by', 'value'),
    Input('sales-date-range', 'start_date'),
    Input('sales-date-range', 'end_date'),
)
def update_sales(group_by, start_date, end_date):
    filtered = sale_lines_df.copy()
    if start_date and end_date:
        start = pd.to_datetime(start_date)
        end = pd.to_datetime(end_date)
        filtered = filtered[(filtered['TRANS_DATE'] >= start) & (filtered['TRANS_DATE'] <= end)]

    # group_by PERIOD column
    if group_by == 'D':
        period_col = filtered['TRANS_DATE'].dt.date.astype(str)
    elif group_by == 'W':
        period_col = filtered['TRANS_DATE'].dt.to_period('W').astype(str)
    elif group_by == 'M':
        period_col = filtered['TRANS_DATE'].dt.to_period('M').astype(str)
    elif group_by == 'Q':
        period_col = filtered['TRANS_DATE'].dt.to_period('Q').astype(str)
    elif group_by == 'A':
        period_col = filtered['TRANS_DATE'].dt.to_period('A').astype(str)
    else:
        period_col = filtered['TRANS_DATE'].dt.date.astype(str)

    sales_agg = (
        filtered
        .assign(PERIOD=period_col)
        .groupby("PERIOD", as_index=False)
        .agg(total_sales=pd.NamedAgg("LINE_TOTAL", "sum"))
        .sort_values("PERIOD")
    )

    # Build figure
    sales_fig = px.line(sales_agg, x="PERIOD", y="total_sales", markers=True, title=f"{group_by} Sales Trend")
    sales_fig = apply_dark_theme(sales_fig)

    # KPI calculations (sales overview)
    total_revenue = filtered["LINE_TOTAL"].sum()
    unique_days = filtered['TRANS_DATE'].dt.date.nunique() if not filtered.empty else 0
    avg_sales_per_day = total_revenue / max(unique_days, 1)
    unique_invoices = filtered['DOC_NUMBER'].nunique() if 'DOC_NUMBER' in filtered.columns else max(len(filtered), 1)
    avg_qty_per_txn = filtered["QUANTITY"].sum() / max(unique_invoices, 1)

    if not sales_agg.empty:
        max_row = sales_agg.loc[sales_agg["total_sales"].idxmax()]
        highest_period = str(max_row["PERIOD"])
        highest_value = float(max_row["total_sales"])
    else:
        highest_period = "N/A"
        highest_value = 0.0

    unique_customers = filtered["CUSTOMER_NUMBER"].nunique() if "CUSTOMER_NUMBER" in filtered.columns else 0

    # KPI cards
    kpi_total = html.Div([
        html.H4("Total Revenue", style={"color": TEXT}),
        html.H3(f"R{total_revenue:,.2f}", style={"color": ACCENT})
    ], style={"width": "18%", "display": "inline-block", "textAlign": "center", "backgroundColor": CARD_BG,
              "borderRadius": "12px", "padding": "12px", "margin": "8px"})

    kpi_avg_day = html.Div([
        html.H4("Avg Sales / Day", style={"color": TEXT}),
        html.H3(f"R{avg_sales_per_day:,.2f}", style={"color": ACCENT})
    ], style={"width": "18%", "display": "inline-block", "textAlign": "center", "backgroundColor": CARD_BG,
              "borderRadius": "12px", "padding": "12px", "margin": "8px"})

    kpi_avg_qty = html.Div([
        html.H4("Avg Qty / Invoice", style={"color": TEXT}),
        html.H3(f"{avg_qty_per_txn:,.2f}", style={"color": ACCENT})
    ], style={"width": "18%", "display": "inline-block", "textAlign": "center", "backgroundColor": CARD_BG,
              "borderRadius": "12px", "padding": "12px", "margin": "8px"})

    kpi_high_day = html.Div([
        html.H4("Highest Sales Period", style={"color": TEXT}),
        html.H3(f"{highest_period} — R{highest_value:,.2f}", style={"color": ACCENT})
    ], style={"width": "18%", "display": "inline-block", "textAlign": "center", "backgroundColor": CARD_BG,
              "borderRadius": "12px", "padding": "12px", "margin": "8px"})

    kpi_unique_cust = html.Div([
        html.H4("Unique Customers", style={"color": TEXT}),
        html.H3(f"{unique_customers}", style={"color": ACCENT})
    ], style={"width": "18%", "display": "inline-block", "textAlign": "center", "backgroundColor": CARD_BG,
              "borderRadius": "12px", "padding": "12px", "margin": "8px"})

    columns = [{"name": str(i), "id": str(i)} for i in sales_agg.columns]
    data = [{k: v for k, v in row.items()} for row in sales_agg.to_dict("records")]
    kpi_children = [kpi_total, kpi_avg_day, kpi_avg_qty, kpi_high_day, kpi_unique_cust]

    return sales_fig, columns, data, kpi_children
@app.callback(
    Output('cust-graph', 'figure'),
    Output('cust-table', 'data'),
    Input('cust-region-filter', 'value')
)
def update_cust_report(regions):
    if not regions:
        filtered = cust_sales
    else:
        filtered = cust_sales[cust_sales['REGION_CODE'].isin(regions)]
    fig = px.bar(filtered.sort_values("total_sales",ascending=False).head(20),
                 x="CUSTOMER_NUMBER",y="total_sales",color="REGION_CODE",
                 title="Top 20 Customers by Sales")
    fig = apply_dark_theme(fig)
    data = [{str(k): str(v) for k, v in row.items()} for row in filtered.astype(str).to_dict("records")]
    return fig, data

@app.callback(
    Output('sup-graph', 'figure'),
    Output('sup-table', 'data'),
    Input('sup-filter', 'value')
)
def update_sup_report(exclsv_codes):
    if not exclsv_codes:
        filtered = suppliers
    else:
        filtered = suppliers[suppliers['EXCLSV'].isin(exclsv_codes)]
    fig = px.bar(filtered.sort_values("CREDIT_LIMIT",ascending=False),
                 x="SUPPLIER_DESC", y="CREDIT_LIMIT", title="Suppliers by Credit Limit")
    fig = apply_dark_theme(fig)
    data = [{str(k): str(v) for k, v in row.items()} for row in filtered.astype(str).to_dict("records")]
    return fig, data

@app.callback(
    Output('trans-graph', 'figure'),
    Input('trans-type-filter', 'value')
)
def update_trans_report(trans_types):
    if not trans_types:
        filtered = sales_hdr
    else:
        filtered = sales_hdr[sales_hdr['TRANSTYPE_CODE'].isin(trans_types)]
    trans_summary = filtered.assign(FINANCIAL_PERIOD=pd.to_datetime(filtered["TRANS_DATE"], errors="coerce").dt.to_period("M").astype(str))
    trans_summary = trans_summary.groupby("FINANCIAL_PERIOD", as_index=False).size().rename(columns={"size":"TRANSACTION_COUNT"})
    trans_fig = px.line(trans_summary,x="FINANCIAL_PERIOD",y="TRANSACTION_COUNT",markers=True,title="Transactions per Month")
    trans_fig = apply_dark_theme(trans_fig)
    return trans_fig

'''@app.callback(
    Output('prod-graph', 'figure'),
    Output('prod-table', 'data'),
    Input('interval-component', 'n_intervals')
)
def update_prod_report(n):
    fig = px.bar(prod_sales.sort_values("total_sales",ascending=False).head(20),
                 x=prod_x_col,y="total_sales",color=prod_color_col,
                 title="Top 20 Products by Sales")
    fig = apply_dark_theme(fig)
    data = [{k: v for k, v in row.items()} for row in prod_sales.to_dict("records")]
    return fig, data
'''
# ---------- DOWNLOAD CALLBACKS ----------
@app.callback(
    Output("sales_download","data"),
   Input("sales_btn","n_clicks"),
   Input("sales-group-by","value"),
  Input("sales-date-range","start_date"),
    Input("sales-date-range","end_date")
)
def download_sales(n, group_by, start_date, end_date):
    if not n: raise PreventUpdate
    filtered = sale_lines_df
    if start_date and end_date:
        start = pd.to_datetime(start_date)
        end = pd.to_datetime(end_date)
        filtered = filtered[(filtered['TRANS_DATE'] >= start) & (filtered['TRANS_DATE'] <= end)]
    if group_by == 'D':
        period_col = filtered['TRANS_DATE'].dt.date.astype(str)
    elif group_by == 'W':
        period_col = filtered['TRANS_DATE'].dt.to_period('W').astype(str)
    elif group_by == 'M':
        period_col = filtered['TRANS_DATE'].dt.to_period('M').astype(str)
    elif group_by == 'Q':
        period_col = filtered['TRANS_DATE'].dt.to_period('Q').astype(str)
    elif group_by == 'A':
        period_col = filtered['TRANS_DATE'].dt.to_period('A').astype(str)
    else:
        period_col = filtered['TRANS_DATE'].dt.date.astype(str)
    sales_agg = filtered.assign(PERIOD=period_col).groupby("PERIOD", as_index=False).agg(total_sales=pd.NamedAgg("LINE_TOTAL","sum")).sort_values("PERIOD")
    return send_data_frame(sales_agg.to_excel,"Sales.xlsx",index=False)

@app.callback(
   Output("cust_download","data"),
   Input("cust_btn","n_clicks"),
   Input("cust-region-filter","value")
)
def download_cust(n, regions):
    if not n: raise PreventUpdate
    if not regions:
        filtered = cust_sales
    else:
        filtered = cust_sales[cust_sales['REGION_CODE'].isin(regions)]
    filtered_top = filtered.sort_values("total_sales", ascending=False).head(20)
    return send_data_frame(filtered_top.to_excel,"Customers.xlsx",index=False)

@app.callback(Output("age_download","data"),Input("age_btn","n_clicks"))
def download_age(n):
    if not n: raise PreventUpdate
    return send_data_frame(age_summary.to_excel,"AgeAnalysis.xlsx",index=False)

@app.callback(Output("trans_download","data"),Input("trans_btn","n_clicks"))
def download_trans(n):
    if not n: raise PreventUpdate
    return send_data_frame(trans_summary.to_excel,"Transactions.xlsx",index=False)

@app.callback(
    Output("sup_download","data"),
    Input("sup_btn","n_clicks"),
    State("sup-filter","value")
)
def download_sup(n, exclsv_codes):
    if not n: raise PreventUpdate
    if not exclsv_codes:
        filtered = suppliers
    else:
        filtered = suppliers[suppliers['EXCLSV'].isin(exclsv_codes)]
    return send_data_frame(filtered.to_excel,"Suppliers.xlsx",index=False)

@app.callback(Output("prod_download","data"),Input("prod_btn","n_clicks"))
def download_prod(n):
    if not n: raise PreventUpdate
    return send_data_frame(prod_sales.to_excel,"Products.xlsx",index=False)

@app.callback(Output("insights_sales_download","data"), Input("insights_sales_btn","n_clicks"))
def download_insights_sales(n):
    if not n: raise PreventUpdate
    df = sale_lines_df.merge(customers[["CUSTOMER_NUMBER","REGION_CODE"]], on="CUSTOMER_NUMBER", how="left")
    df = df.groupby(["FINANCIAL_PERIOD","REGION_CODE"], as_index=False)["LINE_TOTAL"].sum()
    return send_data_frame(df.to_excel,"MonthlySalesByRegion.xlsx", index=False)

@app.callback(Output("insights_sup_download","data"), Input("insights_sup_btn","n_clicks"))
def download_insights_sup(n):
    if not n: raise PreventUpdate
    df = suppliers.sort_values("CREDIT_LIMIT", ascending=False).head(20)
    return send_data_frame(df.to_excel,"TopSuppliers.xlsx", index=False)

@app.callback(Output("insights_prod_download","data"), Input("insights_prod_btn","n_clicks"))
def download_insights_prod(n):
    if not n: raise PreventUpdate
    df = prod_sales.sort_values("total_sales", ascending=False).head(20)
    return send_data_frame(df.to_excel,"TopProducts.xlsx", index=False)

# ---------- DOWNLOAD CALLBACK FOR BI TAB ----------
@app.callback(Output("bi_download", "data"), Input("bi_btn", "n_clicks"))
def download_bi(n):
    if not n:
        raise PreventUpdate
    kpi_data = {
        "Gross Revenue": [sale_lines_df["LINE_TOTAL"].sum()],
        "Average Order Value": [sale_lines_df["LINE_TOTAL"].sum() / max(len(sales_hdr),1)],
        "Monthly Growth Rate (%)": [(
            (sale_lines_df.groupby(sale_lines_df["TRANS_DATE"].dt.to_period("M"))["LINE_TOTAL"].sum().pct_change().fillna(0).iloc[-1]) * 100
        )],
        "Top Region": [cust_sales.groupby("REGION_CODE")["total_sales"].sum().idxmax() if not cust_sales.empty else "N/A"],
        "Top 5 Customers % of Sales": [
            (cust_sales.sort_values("total_sales", ascending=False).head(5)["total_sales"].sum() / max(cust_sales["total_sales"].sum(),1) * 100)
        ]
    }
    df_kpi = pd.DataFrame(kpi_data)
    return send_data_frame(df_kpi.to_excel, "BI_KPIs.xlsx", index=False)

# === NEW SECTION: KAFKA INTEGRATION ===
from kafka import KafkaConsumer
import threading
import json
import time

# Kafka settings
KAFKA_BROKER = os.environ.get("KAFKA_BROKER", "localhost:9092")
KAFKA_TOPIC = os.environ.get("KAFKA_TOPIC", "payment_transactions")

def kafka_consumer_thread():
    """Background thread to consume real-time transactions from Kafka and insert into MongoDB"""
    try:
        consumer = KafkaConsumer(
            KAFKA_TOPIC,
            bootstrap_servers=[KAFKA_BROKER],
            auto_offset_reset='latest',
            enable_auto_commit=True,
            value_deserializer=lambda x: json.loads(x.decode('utf-8'))
        )
        print(f"✅ Listening to Kafka topic '{KAFKA_TOPIC}' for real-time transactions...")
        for message in consumer:
            data = message.value
            if data is None:
                continue
            data["timestamp"] = time.time()
            print(f"📥 Received Kafka message: {data}")

            # Save to MongoDB collection (you can store in a new collection)
            db["RealTime_Transactions"].insert_one(data)
    except Exception as e:
        print("⚠️ Kafka listener error:", e)

# Start background Kafka listener
threading.Thread(target=kafka_consumer_thread, daemon=True).start()



#@app.callback(
#    Output("trans_download","data", allow_duplicate=True),
#    Input("interval-component","n_intervals"),
#    prevent_initial_call="initial_duplicate"
#)
def update_realtime_data(n):
    """Auto-refresh MongoDB data and update app state with new Kafka messages"""
    if db is None:
        raise PreventUpdate
    global sale_lines_df

    # Load new transactions
    new_data = pd.DataFrame([d for d in list(db["RealTime_Transactions"].find()) if d is not None])
    if not new_data.empty:
        new_data["TRANS_DATE"] = pd.to_datetime(new_data["TRANS_DATE"] if "TRANS_DATE" in new_data.columns else pd.Timestamp.now(), errors="coerce")
        if "QUANTITY" in new_data.columns:
            new_data["QUANTITY"] = pd.to_numeric(new_data["QUANTITY"], errors="coerce").fillna(0)
        else:
            new_data["QUANTITY"] = 0
        if "UNIT_SELL_PRICE" in new_data.columns:
            new_data["UNIT_SELL_PRICE"] = pd.to_numeric(new_data["UNIT_SELL_PRICE"], errors="coerce").fillna(0)
        else:
            new_data["UNIT_SELL_PRICE"] = 0
        new_data["LINE_TOTAL"] = new_data["QUANTITY"] * new_data["UNIT_SELL_PRICE"]
        sale_lines_df = pd.concat([sale_lines_df, new_data], ignore_index=True)
    raise PreventUpdate

# ---------- RUN APP ----------
if __name__=="__main__":
    app.run(debug=True,host="127.0.0.1",port=8050)

app = Dash(__name__)
server = app.server
