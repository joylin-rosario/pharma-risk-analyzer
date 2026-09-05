# Pharma Supply Chain Risk Analyzer

A mini Streamlit app that reads a pharma shipment workbook and flags high-risk
shipments (cold-chain breaches, delivery/customs delays, damaged or
undocumented cargo, near-expiry stock, high-risk suppliers/destinations,
controlled-substance diversion risk).

## Run it

```bash
pip install -r requirements.txt
streamlit run app.py
```

The app defaults to the bundled sample workbook at `data/pharma_supply_chain.xlsx`.
Use the sidebar file uploader to swap in a different `.xlsx` with the same schema.

## Regenerate the sample dataset

`data/pharma_supply_chain.xlsx` is synthetic (no real shipment data). Regenerate
it with:

```bash
python generate_data.py
```

This is a fixed-seed generator (`np.random.default_rng(42)`), so re-running it
reproduces the same 320 rows unless you edit the script. Poor-supplier rows are
deliberately biased toward more delays/damage/missing docs so the risk
distribution includes a few genuine "Critical" examples, not just "High".

There is also a `/regen-data` skill
([.claude/skills/regen-data.md](.claude/skills/regen-data.md)) that runs the
above and then sanity-checks the output against `risk_engine.validate_columns`
and the `Risk_Category` distribution — prefer it over the bare command when
you've just edited `generate_data.py`, since it catches a broken risk
correlation (e.g. the `Critical` band silently dropping to zero) before you
notice it in the app.

## Files

- `app.py` — Streamlit UI: filters, KPI tiles, Plotly charts, flagged-shipment
  table with CSV export.
- `risk_engine.py` — pure scoring logic (`score_shipments`, `validate_columns`).
  Kept separate from `app.py` so the rules can be unit-tested or reused without
  Streamlit.
- `generate_data.py` — synthetic dataset generator.
- `data/pharma_supply_chain.xlsx` — bundled sample workbook (sheet: `Shipments`).

## Dataset schema

The workbook must have a sheet named `Shipments` with these columns
(`risk_engine.validate_columns` checks for them and the app shows a clear error
if any are missing):

| Column | Type | Notes |
|---|---|---|
| `Shipment_ID` | str | unique ID |
| `Product_Name` | str | |
| `Product_Category` | str | Vaccine / Biologic / Generic / OTC / Controlled Substance |
| `Requires_Cold_Chain` | bool | whether temp range applies |
| `Origin_Country` | str | |
| `Destination_Country` | str | |
| `Carrier` | str | |
| `Ship_Date` | date | |
| `Expected_Delivery_Date` | date | |
| `Actual_Delivery_Date` | date | |
| `Min_Temp_C` / `Max_Temp_C` | float | required range; NaN if not cold-chain |
| `Recorded_Min_Temp_C` / `Recorded_Max_Temp_C` | float | actual in-transit extremes |
| `Customs_Delay_Days` | int | |
| `Documentation_Complete` | bool | |
| `Packaging_Damaged` | bool | |
| `Supplier_Risk_Rating` | str | Low / Medium / High |
| `Quantity_Units` | int | |
| `Value_USD` | float | |
| `Expiry_Date` | date | |

## Risk scoring model (`risk_engine.score_shipments`)

Each shipment gets a 0–100 `Risk_Score`, additive across independent factors,
plus a human-readable `Risk_Factors` string so a flag is always explainable —
never a black-box number:

| Factor | Points |
|---|---|
| Cold-chain temperature excursion | up to 30, scaled by °C beyond range |
| Delivery delay vs. expected date | up to 20 (4 pts/day) |
| Customs delay | up to 10 (2 pts/day) |
| Incomplete documentation | flat 15 |
| Packaging damaged | flat 15 |
| Supplier risk rating | 0 / 8 / 18 (Low/Medium/High) |
| Near-expiry at delivery | 15 (≤30 days), 7 (≤90 days) |
| High-risk destination market | flat 10 |
| High-value controlled substance (>$50k) | flat 10 (diversion risk) |

Score bands: **Low** 0–24, **Medium** 25–49, **High** 50–74, **Critical** 75+.
"High-risk shipments" in the UI means High or Critical band, or the sidebar's
adjustable minimum-score filter.

Thresholds and weights live as constants at the top of `risk_engine.py`
(`HIGH_RISK_DESTINATIONS`, `CONTROLLED_SUBSTANCE_VALUE_THRESHOLD`,
`RISK_BANDS`) — adjust there, not in `app.py`.

## Conventions for this repo

- Keep scoring logic in `risk_engine.py`, not in `app.py`. The app should only
  read/filter/display; anyone should be able to `import risk_engine` and score
  a DataFrame without Streamlit.
- Don't add new risk factors as opaque numbers — always append a matching
  entry to `Risk_Factors` so every flagged shipment stays auditable.
- Chart colors follow the project's data-viz palette: status colors
  (`Low`/`Medium`/`High`/`Critical` → green/amber/orange/red) are reserved for
  risk bands and never reused for categorical series; product categories use
  the fixed categorical order (blue, orange, aqua, yellow, magenta). Keep new
  charts consistent with this rather than picking colors ad hoc.
- This is a "mini" demo tool: prefer the simplest change that works over new
  abstractions, config layers, or a database. If real shipment data with a
  different schema shows up, extend `REQUIRED_COLUMNS`/`validate_columns`
  rather than silently coercing unknown columns.
