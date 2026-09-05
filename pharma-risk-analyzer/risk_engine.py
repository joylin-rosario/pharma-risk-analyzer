"""Risk scoring logic for pharma supply-chain shipments.

Expects a DataFrame shaped like data/pharma_supply_chain.xlsx (see CLAUDE.md
for the column reference). Adds a Risk_Score (0-100), Risk_Category, and a
Risk_Factors string explaining which rules fired, so flags are auditable
rather than a black-box number.
"""
import numpy as np
import pandas as pd

REQUIRED_COLUMNS = [
    "Shipment_ID", "Product_Category", "Requires_Cold_Chain",
    "Destination_Country", "Ship_Date", "Expected_Delivery_Date",
    "Actual_Delivery_Date", "Min_Temp_C", "Max_Temp_C",
    "Recorded_Min_Temp_C", "Recorded_Max_Temp_C", "Customs_Delay_Days",
    "Documentation_Complete", "Packaging_Damaged", "Supplier_Risk_Rating",
    "Value_USD", "Expiry_Date",
]

HIGH_RISK_DESTINATIONS = {"Nigeria", "Venezuela", "Pakistan", "Myanmar"}
CONTROLLED_SUBSTANCE_VALUE_THRESHOLD = 50_000

RISK_BANDS = [
    (75, "Critical"),
    (50, "High"),
    (25, "Medium"),
    (0, "Low"),
]


def validate_columns(df: pd.DataFrame) -> list[str]:
    return [c for c in REQUIRED_COLUMNS if c not in df.columns]


def _categorize(score: float) -> str:
    for threshold, label in RISK_BANDS:
        if score >= threshold:
            return label
    return "Low"


def score_shipments(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    for date_col in ["Ship_Date", "Expected_Delivery_Date", "Actual_Delivery_Date", "Expiry_Date"]:
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce")

    scores = np.zeros(len(df))
    factors = [[] for _ in range(len(df))]

    # 1. Cold-chain temperature excursion (up to 30 pts, scaled by magnitude)
    cold_chain = df["Requires_Cold_Chain"].astype(bool)
    excursion_low = (df["Min_Temp_C"] - df["Recorded_Min_Temp_C"]).clip(lower=0)
    excursion_high = (df["Recorded_Max_Temp_C"] - df["Max_Temp_C"]).clip(lower=0)
    excursion = pd.concat([excursion_low, excursion_high], axis=1).max(axis=1).fillna(0)
    excursion_pts = (excursion * 6).clip(upper=30)
    excursion_pts = np.where(cold_chain, excursion_pts, 0)
    scores += excursion_pts
    for i in np.where((excursion_pts > 0))[0]:
        factors[i].append(f"Temperature excursion ({excursion.iloc[i]:.1f}°C outside range)")

    # 2. Delivery delay vs expected (up to 20 pts)
    delay_days = (df["Actual_Delivery_Date"] - df["Expected_Delivery_Date"]).dt.days.clip(lower=0).fillna(0)
    delay_pts = (delay_days * 4).clip(upper=20)
    scores += delay_pts
    for i in np.where(delay_days >= 2)[0]:
        factors[i].append(f"Delivery delay ({int(delay_days.iloc[i])} days late)")

    # 3. Customs delay (up to 10 pts)
    customs_days = df["Customs_Delay_Days"].fillna(0)
    customs_pts = (customs_days * 2).clip(upper=10)
    scores += customs_pts
    for i in np.where(customs_days >= 3)[0]:
        factors[i].append(f"Customs delay ({int(customs_days.iloc[i])} days)")

    # 4. Documentation incomplete (flat 15 pts)
    doc_missing = ~df["Documentation_Complete"].astype(bool)
    scores += np.where(doc_missing, 15, 0)
    for i in np.where(doc_missing)[0]:
        factors[i].append("Incomplete documentation")

    # 5. Packaging damaged (flat 15 pts)
    damaged = df["Packaging_Damaged"].astype(bool)
    scores += np.where(damaged, 15, 0)
    for i in np.where(damaged)[0]:
        factors[i].append("Packaging damaged")

    # 6. Supplier risk rating (0 / 8 / 18 pts)
    supplier_pts = df["Supplier_Risk_Rating"].map({"Low": 0, "Medium": 8, "High": 18}).fillna(0)
    scores += supplier_pts
    for i in np.where(supplier_pts >= 18)[0]:
        factors[i].append("High-risk supplier")

    # 7. Near-expiry at delivery (15 pts <=30 days, 7 pts <=90 days)
    days_to_expiry = (df["Expiry_Date"] - df["Actual_Delivery_Date"]).dt.days
    near_expiry_pts = np.select(
        [days_to_expiry <= 30, days_to_expiry <= 90],
        [15, 7],
        default=0,
    )
    scores += near_expiry_pts
    for i in np.where(near_expiry_pts > 0)[0]:
        factors[i].append(f"Near expiry at delivery ({int(days_to_expiry.iloc[i])} days remaining)")

    # 8. High-risk destination (flat 10 pts)
    dest_risk = df["Destination_Country"].isin(HIGH_RISK_DESTINATIONS)
    scores += np.where(dest_risk, 10, 0)
    for i in np.where(dest_risk)[0]:
        factors[i].append("High-risk destination market")

    # 9. Controlled substance + high value (diversion risk, flat 10 pts)
    diversion = (df["Product_Category"] == "Controlled Substance") & (df["Value_USD"] > CONTROLLED_SUBSTANCE_VALUE_THRESHOLD)
    scores += np.where(diversion, 10, 0)
    for i in np.where(diversion)[0]:
        factors[i].append("High-value controlled substance (diversion risk)")

    df["Risk_Score"] = np.clip(scores, 0, 100).round(1)
    df["Risk_Category"] = df["Risk_Score"].apply(_categorize)
    df["Risk_Factors"] = ["; ".join(f) if f else "No flags" for f in factors]

    # Exposed for charting/inspection alongside the score breakdown above.
    df["Temp_Excursion_C"] = excursion.round(1)
    df["Delivery_Delay_Days"] = delay_days.astype(int)
    df["Days_To_Expiry_At_Delivery"] = days_to_expiry

    return df
