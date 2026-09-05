"""Generates a synthetic pharma supply-chain shipment dataset for the risk analyzer.

Run: python generate_data.py
Output: data/pharma_supply_chain.xlsx
"""
import numpy as np
import pandas as pd

rng = np.random.default_rng(42)

N = 320

PRODUCT_CATALOG = [
    ("Vaxinol Booster", "Vaccine", True, 2, 8),
    ("Immunar Shot", "Vaccine", True, 2, 8),
    ("Insulmax Pen", "Biologic", True, 2, 8),
    ("Onco-Rituxil", "Biologic", True, -20, -10),
    ("Neurostat Infusion", "Biologic", True, 2, 8),
    ("Cardiozan Tablets", "Generic", False, 15, 25),
    ("Metfortin 500mg", "Generic", False, 15, 25),
    ("Amoxiclear Susp.", "Generic", False, 15, 25),
    ("Painex Extra", "OTC", False, 15, 30),
    ("Dermacort Cream", "OTC", False, 15, 30),
    ("Fentris Patch", "Controlled Substance", False, 15, 25),
    ("Oxycodex 10mg", "Controlled Substance", False, 15, 25),
]

ORIGINS = ["India", "Germany", "USA", "Switzerland", "Ireland", "China", "Singapore", "Brazil"]

# Simplified illustrative risk tiers for transit/customs friction - for demo purposes only,
# not an official trade-compliance or sanctions reference.
DESTINATIONS = {
    "USA": "low", "Germany": "low", "Canada": "low", "Japan": "low",
    "UK": "low", "France": "low", "Australia": "low",
    "Brazil": "medium", "India": "medium", "Mexico": "medium",
    "South Africa": "medium", "Indonesia": "medium",
    "Nigeria": "high", "Venezuela": "high", "Pakistan": "high", "Myanmar": "high",
}

CARRIERS = ["AeroFreight Global", "ColdLink Logistics", "PharmaCarry Express",
            "TransWorld Cargo", "MedRoute Air", "OceanBridge Shipping"]

SUPPLIER_RISK = ["Low", "Medium", "High"]

dest_names = list(DESTINATIONS.keys())
dest_weights = np.array([3 if DESTINATIONS[d] == "low" else 2 if DESTINATIONS[d] == "medium" else 1
                          for d in dest_names], dtype=float)
dest_weights /= dest_weights.sum()

rows = []
start_date = pd.Timestamp("2026-01-01")

for i in range(1, N + 1):
    product_name, category, cold_chain, min_t, max_t = PRODUCT_CATALOG[rng.integers(0, len(PRODUCT_CATALOG))]
    origin = rng.choice(ORIGINS)
    destination = rng.choice(dest_names, p=dest_weights)
    carrier = rng.choice(CARRIERS)

    ship_date = start_date + pd.Timedelta(days=int(rng.integers(0, 240)))
    transit_days_expected = int(rng.integers(3, 12))
    expected_delivery = ship_date + pd.Timedelta(days=transit_days_expected)

    # Supplier risk is drawn first: poor suppliers correlate with more downstream
    # problems (delays, damage, missing paperwork), which is realistic and also
    # produces a handful of genuinely compounding, "Critical" shipments.
    supplier_risk = rng.choice(SUPPLIER_RISK, p=[0.6, 0.28, 0.12])
    trouble_bias = {"Low": 0.0, "Medium": 0.15, "High": 0.35}[supplier_risk]

    # Delay: mostly on-time/small delay, occasional big delay
    delay_roll = rng.random()
    if delay_roll < 0.65 - trouble_bias:
        delay_days = int(rng.integers(0, 2))
    elif delay_roll < 0.90 - trouble_bias:
        delay_days = int(rng.integers(2, 6))
    else:
        delay_days = int(rng.integers(6, 15))
    actual_delivery = expected_delivery + pd.Timedelta(days=delay_days)

    customs_roll = rng.random()
    customs_delay_days = 0
    if DESTINATIONS[destination] == "high":
        customs_delay_days = int(rng.integers(0, 10)) if customs_roll < 0.7 + trouble_bias else int(rng.integers(0, 3))
    elif DESTINATIONS[destination] == "medium":
        customs_delay_days = int(rng.integers(0, 5)) if customs_roll < 0.4 + trouble_bias else 0
    else:
        customs_delay_days = int(rng.integers(0, 2)) if customs_roll < 0.15 + trouble_bias else 0

    # Temperature excursion, only meaningful for cold-chain products
    if cold_chain:
        excursion_roll = rng.random()
        if excursion_roll < 0.72 - trouble_bias:
            recorded_min = min_t + rng.uniform(0.2, 1.5)
            recorded_max = max_t - rng.uniform(0.2, 1.5)
        elif excursion_roll < 0.90 - trouble_bias * 0.5:
            recorded_min = min_t - rng.uniform(0.5, 2.5)
            recorded_max = max_t + rng.uniform(0.5, 2.5)
        else:
            recorded_min = min_t - rng.uniform(2.5, 6.0)
            recorded_max = max_t + rng.uniform(2.5, 8.0)
        recorded_min = round(recorded_min, 1)
        recorded_max = round(recorded_max, 1)
    else:
        recorded_min, recorded_max = np.nan, np.nan

    documentation_complete = rng.random() > (0.10 + trouble_bias)
    packaging_damaged = rng.random() < (0.08 + trouble_bias * 0.6)

    quantity_units = int(rng.integers(200, 20000))
    unit_value = {
        "Vaccine": rng.uniform(8, 25),
        "Biologic": rng.uniform(40, 150),
        "Generic": rng.uniform(0.1, 1.5),
        "OTC": rng.uniform(0.2, 2.0),
        "Controlled Substance": rng.uniform(2, 10),
    }[category]
    value_usd = round(quantity_units * unit_value, 2)

    shelf_life_days = {
        "Vaccine": rng.integers(180, 540),
        "Biologic": rng.integers(365, 900),
        "Generic": rng.integers(540, 1100),
        "OTC": rng.integers(540, 1100),
        "Controlled Substance": rng.integers(540, 1100),
    }[category]
    expiry_date = ship_date + pd.Timedelta(days=int(shelf_life_days))

    rows.append({
        "Shipment_ID": f"SHP-{2600 + i}",
        "Product_Name": product_name,
        "Product_Category": category,
        "Requires_Cold_Chain": cold_chain,
        "Origin_Country": origin,
        "Destination_Country": destination,
        "Carrier": carrier,
        "Ship_Date": ship_date,
        "Expected_Delivery_Date": expected_delivery,
        "Actual_Delivery_Date": actual_delivery,
        "Min_Temp_C": min_t if cold_chain else np.nan,
        "Max_Temp_C": max_t if cold_chain else np.nan,
        "Recorded_Min_Temp_C": recorded_min,
        "Recorded_Max_Temp_C": recorded_max,
        "Customs_Delay_Days": customs_delay_days,
        "Documentation_Complete": documentation_complete,
        "Packaging_Damaged": packaging_damaged,
        "Supplier_Risk_Rating": supplier_risk,
        "Quantity_Units": quantity_units,
        "Value_USD": value_usd,
        "Expiry_Date": expiry_date,
    })

df = pd.DataFrame(rows)
out_path = "data/pharma_supply_chain.xlsx"
df.to_excel(out_path, sheet_name="Shipments", index=False)
print(f"Wrote {len(df)} rows to {out_path}")
