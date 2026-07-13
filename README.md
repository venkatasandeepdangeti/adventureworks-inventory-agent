# AdventureWorks Inventory & Restocking Agent

**🔗 Live demo (no setup required): https://adventureworks-inventory-agent.streamlit.app/**

Ask a question in plain English about inventory, restocking, vendors, or purchasing — get back the generated SQL, the result, and a one-sentence explanation. Built on **real data** from Microsoft's official [AdventureWorks sample database](https://github.com/microsoft/sql-server-samples), not synthetic data.

## What it can answer
- **Restocking**: "Which products are below their reorder point?"
- **Vendor/lead-time**: "Which vendor has the longest average lead time?"
- **Warehouse/location**: "Which warehouse location has the most inventory on hand?"

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env   # then edit .env and set a real API key (Groq/Gemini/Anthropic)
python load_data.py    # downloads real AdventureWorks CSVs and builds data/adventureworks.duckdb
streamlit run app.py
```

## Data
`load_data.py` downloads 9 tables directly from Microsoft's official GitHub repo (no SQL Server needed):
`product`, `product_category`, `product_subcategory`, `product_inventory`, `location`, `vendor`, `product_vendor`, `purchase_order_header`, `purchase_order_detail` — the real, standard AdventureWorks row counts (504 products, 4,012 purchase orders, etc.)

## Safety
- Only `SELECT`/`WITH` statements are ever executed; anything else (INSERT/UPDATE/DELETE/DROP/ALTER/etc.) is rejected before running.
- The DuckDB connection opens read-only.
- Generated SQL is always shown to the user before/alongside execution.

## Known issue: crashes on ARM64 (aarch64) Linux
If Streamlit segfaults shortly after asking a question, this is a known pyarrow bug (jemalloc background thread) on ARM64. Fix:
```bash
export ARROW_DEFAULT_MEMORY_POOL=system
streamlit run app.py
```
