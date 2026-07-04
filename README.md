# ClearVue Integrated Business Dashboard

A real-time, NoSQL-backed sales reporting system built for ClearVue Ltd., replacing a legacy MS Access setup that struggled to scale with the company's growing product- and supplier-side business. The system ingests sales, customer, product, and supplier data into MongoDB, streams new transactions in live via Kafka, and surfaces everything through an interactive Plotly Dash dashboard.

![ClearVue Integrated Business Dashboard](clearvue_dashboard.png)

This was a group project (7 members) developed as a client-style engineering brief. My contributions focused on data transformation logic, dashboard visualisations, and the MongoDB integration layer.

## Why this exists

ClearVue needed a reporting system that could:
- Handle daily, weekly, monthly, and yearly views of sales performance
- Adapt to new data structures as the business shifts toward supplier-side operations
- Support real-time updates instead of static, manually refreshed reports
- Replace a brittle MS Access solution that couldn't keep pace with the company's data

## Features

The dashboard is organised into tabs, each targeting a different reporting need:

- **📈 BI Metrics (Managers)** — executive KPIs: gross revenue, average order value, monthly growth rate, top region, and top-5-customer sales concentration
- **💰 Sales Overview** — revenue and growth trends over time
- **🧾 Customer Report** — top customers by sales, segmented by region
- **📅 Age Analysis** — outstanding balances by aging bucket (current, 30/60/90+ days)
- **🔁 Transactions** — transaction volume by financial period
- **🏭 Supplier Report** — supplier credit exposure and spend
- **🛒 Product Report** — sales performance by product and brand
- **📊 Key Insights** — supporting summary visualisations

A custom **financial calendar** implementation correctly maps transaction dates to ClearVue's fiscal periods, where each financial month runs from the last Saturday of the preceding month to the last Friday of the current month — including handling for year boundaries and leap years.

## Architecture

| Layer | Technology |
|---|---|
| Database | MongoDB (NoSQL, document-based collections) |
| Real-time ingestion | Apache Kafka (streams new transactions into MongoDB as they occur) |
| Data processing | Python — Pandas (cleaning, transformation, aggregation) |
| Visualisation | Plotly & Dash (interactive dashboard) |
| Hosting | Local prototype |

MongoDB collections: `Sales_Header`, `Sales_Lines`, `Customers`, `Products`, `Product_Brands`, `Product_Categories`, `Suppliers`, `Age_Analysis`.

A background Kafka consumer thread listens for new transaction messages and writes them into a `RealTime_Transactions` collection, which the dashboard picks up to reflect live activity without a manual refresh.

If MongoDB is unreachable, the app falls back to small built-in sample datasets so the dashboard still renders for demo purposes.

## Getting started

### Prerequisites
- Python 3.9+
- A MongoDB Atlas cluster (or local MongoDB instance)
- A running Kafka broker (optional — only needed for the real-time ingestion feature; the dashboard runs fine without it using data already in MongoDB)

### Installation

```bash
git clone https://github.com/kl99-chi/clearvue-reporting-system.git
cd clearvue-reporting-system
pip install -r requirements.txt
```

### Configuration

The app reads its connection settings from environment variables — **no credentials are hardcoded**:

```bash
export MONGO_URI="mongodb+srv://<user>:<password>@<cluster-url>/"
export DB_NAME="ClearVu_Ltd"
export KAFKA_BROKER="localhost:9092"      # optional, only for live ingestion
export KAFKA_TOPIC="payment_transactions"  # optional, only for live ingestion
```

> ⚠️ Never commit real database credentials to source control. Use a `.env` file (excluded via `.gitignore`) or your platform's secret manager instead.

### Running

```bash
python that.py
```

The dashboard will be available at `http://127.0.0.1:8050`.

## requirements.txt

```
pandas
plotly
dash
pymongo
certifi
kafka-python
```

## Lessons learned

- **Query optimisation is manual in NoSQL.** Some unindexed queries took up to twelve seconds against large collections; adding indexes on frequently-filtered fields (e.g. customer number, financial period) brought this under two seconds.
- **Business date logic is deceptively complex.** ClearVue's custom financial calendar produced incorrect results for several months per year until covered by comprehensive unit tests across all twelve months and multiple years.
- **Data migration is most of the work.** Cleaning inconsistent date formats, NULL representations, and duplicate/orphaned records consumed roughly a third of total project time.
- **Technology is half the solution.** A technically sound system still depends on user adoption, training, and change management to succeed.

## Team

Built by a 7-person group as part of an academic client-engagement project (ClearVue Ltd. brief), October 2025.

---

*Part of my portfolio — see the live case study at (https://keletso-ramothibe-portfolio-website.netlify.app/).*
