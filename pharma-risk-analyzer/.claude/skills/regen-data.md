---
name: regen-data
description: Regenerate the bundled synthetic pharma shipment dataset and sanity-check it against risk_engine. Use after editing generate_data.py, or whenever a fresh sample workbook is needed.
---

# regen-data

Runs `generate_data.py` from the repo root.

**Output**: overwrites `data/pharma_supply_chain.xlsx` (sheet `Shipments`).
Generation is fixed-seed (`np.random.default_rng(42)`), so re-running with an
unmodified script reproduces the same 320 rows — only edits to
`generate_data.py` change the output.

**Steps**:
1. `python generate_data.py`
2. Load the new workbook and confirm it still matches the schema
   `risk_engine.validate_columns` expects — the check should return an empty
   list:
   ```bash
   python -c "
   import pandas as pd
   from risk_engine import score_shipments, validate_columns
   df = pd.read_excel('data/pharma_supply_chain.xlsx', sheet_name='Shipments')
   print('missing columns:', validate_columns(df))
   print(score_shipments(df)['Risk_Category'].value_counts())
   "
   ```
3. Report the new `Risk_Category` distribution to the user. Flag it if the
   `Critical` band drops to zero — the generator deliberately biases
   high-risk suppliers toward compounding problems so at least a couple of
   Critical examples exist for the dashboard to show; a zero count usually
   means a change to `generate_data.py` broke that correlation.

**When to use**: after changing risk categories, product catalog, or
probability rolls in `generate_data.py`; not needed for changes to
`risk_engine.py` or `app.py` alone.
