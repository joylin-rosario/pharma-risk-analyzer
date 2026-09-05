# Pharma Supply Chain Risk Analyzer

A mini Streamlit app that reads a pharma shipment workbook and flags
high-risk shipments — cold-chain breaches, delivery/customs delays, damaged
or undocumented cargo, near-expiry stock, high-risk suppliers/destinations,
and controlled-substance diversion risk.

## Features

- Upload any `.xlsx` shipment workbook, or use the bundled synthetic sample
- Every shipment gets a 0–100 risk score **and** a plain-English list of which
  rules fired — never a black-box number
- Filterable dashboard: KPI tiles, risk-distribution charts, temperature
  excursion vs. risk scatter, top high-risk destinations
- Sortable table of flagged shipments with CSV export

## Quickstart

```bash
git clone https://github.com/joylin-rosario/pharma-risk-analyzer.git
cd pharma-risk-analyzer
pip install -r requirements.txt
streamlit run app.py
```

Open the URL Streamlit prints (defaults to `http://localhost:8501`). Use the
sidebar to upload your own workbook or keep the bundled sample.

## How risk is scored

Each shipment accumulates points across independent factors, capped at 100:

| Factor | Points |
|---|---|
| Cold-chain temperature excursion | up to 30 |
| Delivery delay vs. expected date | up to 20 |
| Customs delay | up to 10 |
| Incomplete documentation | 15 |
| Packaging damaged | 15 |
| Supplier risk rating (Low/Medium/High) | 0 / 8 / 18 |
| Near-expiry at delivery | 15 (≤30 days) / 7 (≤90 days) |
| High-risk destination market | 10 |
| High-value controlled substance | 10 |

Bands: **Low** 0–24 · **Medium** 25–49 · **High** 50–74 · **Critical** 75+.
See [`risk_engine.py`](risk_engine.py) for the exact logic and
[CLAUDE.md](CLAUDE.md) for the full column schema and scoring reference.

## Sample dataset

`data/pharma_supply_chain.xlsx` is a synthetic, fixed-seed dataset (320
shipments) — **not real shipment data**. Regenerate it with:

```bash
python generate_data.py
```

## Project structure

```
app.py              Streamlit UI (filters, KPI tiles, charts, table)
risk_engine.py       Scoring logic, usable standalone (no Streamlit needed)
generate_data.py     Synthetic dataset generator
data/                Bundled sample workbook
CLAUDE.md            Schema reference + conventions for extending this repo
```

## Disclaimer

This is a demo/training project. The risk model and country risk tiers are
simplified for illustration and are **not** a compliance, trade-sanctions, or
regulatory tool — don't use it for real pharmacovigilance or logistics
decisions without independent validation.
