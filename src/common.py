"""Shared helpers for every analysis: loading, the sales definition, and the
publication rule that no group smaller than MIN_N orders may be published."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "orders_anon.parquet"
TABLES = ROOT / "outputs" / "tables"
MIN_N = 50

# Display order for the sales channels (Unknown kept last, never compared)
CHANNELS = ["TikTok Live", "Facebook Page", "Instagram", "Website (Shopify)", "Unknown"]


# Socio-economic "littoral / interieur" split (confirmed by the author).
# Manouba counted coastal as part of Greater Tunis; Beja and Jendouba counted
# interior as part of the North-West despite a short coastline.
COASTAL = {"Tunis", "Ariana", "Ben Arous", "Manouba", "Nabeul", "Bizerte", "Sousse",
           "Monastir", "Mahdia", "Sfax", "Gabes", "Medenine"}
POPULATION = ROOT / "reference" / "ins_population_2024.csv"  # INS RGPH 2024, p.15


def region(gov: str) -> str:
    return "Coastal" if gov in COASTAL else "Interior"


def load() -> pd.DataFrame:
    return pd.read_parquet(DATA)


def sales(df: pd.DataFrame) -> pd.DataFrame:
    """A sale = not a complaint follow-up (Reclamation) and order_total > 0."""
    out = df[(df["channel"] != "Reclamation") & (df["order_total"] > 0)].copy()
    out["channel"] = out["channel"].cat.remove_unused_categories()
    return out


def save_table(table: pd.DataFrame, name: str, n_col: str = "orders") -> Path:
    """Write a publishable table. Refuses if any group has fewer than MIN_N orders."""
    small = table[table[n_col] < MIN_N]
    if len(small):
        raise ValueError(f"{name}: {len(small)} group(s) below {MIN_N} orders - suppress before saving")
    TABLES.mkdir(parents=True, exist_ok=True)
    path = TABLES / f"{name}.csv"
    table.to_csv(path, index=False)
    return path


def suppress(table: pd.DataFrame, n_col: str = "orders") -> pd.DataFrame:
    """Drop groups below MIN_N (used for fine-grained cross-tabs)."""
    return table[table[n_col] >= MIN_N].copy()
