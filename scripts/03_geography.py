"""Analysis 2 - geography.

Orders, revenue and customers per governorate, normalized by population
(INS RGPH 2024) as orders and customers per 1,000 inhabitants, plus a
coastal vs interior comparison. Scope: sales only, known governorate.
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.common import POPULATION, load, region, sales, save_table  # noqa: E402

s = sales(load())
n_unknown = int((s["governorate"] == "Unknown").sum())
s = s[s["governorate"] != "Unknown"].copy()
s["governorate"] = s["governorate"].cat.remove_unused_categories()
print(f"Sales with known governorate: {len(s):,} (Unknown excluded: {n_unknown})")

# diagnostic: customers whose orders span several governorates
gpc = s.groupby("customer_id")["governorate"].nunique()
print(f"Customers ordering to >1 governorate: {int((gpc > 1).sum()):,} ({100 * (gpc > 1).mean():.1f}%)")

pop = pd.read_csv(POPULATION).set_index("governorate")["population_2024"]
g = s.groupby("governorate", observed=True)
t = pd.DataFrame({
    "orders": g.size(),
    "revenue_tnd": g["order_total"].sum(),
    "customers": g["customer_id"].nunique(),
    "median_basket": g["order_total"].median(),
    "mean_basket": g["order_total"].mean(),
})
t["population_2024"] = pop
t["region"] = [region(x) for x in t.index]
t["share_orders_pct"] = 100 * t["orders"] / t["orders"].sum()
t["share_revenue_pct"] = 100 * t["revenue_tnd"] / t["revenue_tnd"].sum()
t["share_population_pct"] = 100 * t["population_2024"] / t["population_2024"].sum()
t["orders_per_1000"] = 1000 * t["orders"] / t["population_2024"]
t["customers_per_1000"] = 1000 * t["customers"] / t["population_2024"]
t["revenue_per_capita_tnd"] = t["revenue_tnd"] / t["population_2024"]
t["orders_per_customer"] = t["orders"] / t["customers"]
nat = 1000 * len(s) / pop.sum()
t["index_vs_national"] = 100 * t["orders_per_1000"] / nat  # 100 = national average
t = t.sort_values("orders_per_1000", ascending=False).rename_axis("governorate").reset_index()
cols = ["governorate", "region", "population_2024", "share_population_pct", "orders", "share_orders_pct",
        "revenue_tnd", "share_revenue_pct", "customers", "orders_per_1000", "customers_per_1000",
        "index_vs_national", "revenue_per_capita_tnd", "orders_per_customer", "median_basket", "mean_basket"]
t = t[cols].round({"share_population_pct": 2, "share_orders_pct": 2, "share_revenue_pct": 2,
                   "orders_per_1000": 1, "customers_per_1000": 1, "index_vs_national": 0,
                   "revenue_per_capita_tnd": 2, "orders_per_customer": 2, "median_basket": 1,
                   "mean_basket": 1, "revenue_tnd": 0})
t["revenue_tnd"] = t["revenue_tnd"].astype("int64")

# Coastal vs interior
s["region"] = s["governorate"].astype(str).map(region)
r = s.groupby("region")
rp = pop.groupby(pop.index.map(region)).sum()
c = pd.DataFrame({
    "governorates": t.groupby("region").size(),
    "population_2024": rp,
    "orders": r.size(),
    "revenue_tnd": r["order_total"].sum(),
    "customers": r["customer_id"].nunique(),
    "median_basket": r["order_total"].median(),
    "mean_basket": r["order_total"].mean(),
})
c["share_population_pct"] = 100 * c["population_2024"] / c["population_2024"].sum()
c["share_orders_pct"] = 100 * c["orders"] / c["orders"].sum()
c["share_revenue_pct"] = 100 * c["revenue_tnd"] / c["revenue_tnd"].sum()
c["orders_per_1000"] = 1000 * c["orders"] / c["population_2024"]
c["customers_per_1000"] = 1000 * c["customers"] / c["population_2024"]
c["revenue_per_capita_tnd"] = c["revenue_tnd"] / c["population_2024"]
c["orders_per_customer"] = c["orders"] / c["customers"]
c = c.rename_axis("region").reset_index().round(2)
c["revenue_tnd"] = c["revenue_tnd"].round(0).astype("int64")

p1 = save_table(t, "02_geography_governorates")
p2 = save_table(c, "02b_coastal_vs_interior")
with pd.option_context("display.width", 260, "display.max_columns", 30):
    print(f"\nNational average: {nat:.1f} orders per 1,000 inhabitants\n")
    print(t.drop(columns=["revenue_tnd", "mean_basket"]).to_string(index=False))
    print("\n" + c.to_string(index=False))
print(f"\nSaved {p1.name}, {p2.name}")
