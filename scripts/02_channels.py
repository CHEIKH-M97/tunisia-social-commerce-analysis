"""Analysis 1 - channel performance.

Share of orders and of order value per channel, plus mean / median basket.
Scope: sales only (Reclamation and zero-value orders excluded).
"Revenue" here = gross order value (sum of order_total, TND), not profit.
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.common import CHANNELS, load, sales, save_table  # noqa: E402

df = load()
s = sales(df)
print(f"All orders {len(df):,} -> sales {len(s):,} "
      f"(excluded: Reclamation {int((df.channel == 'Reclamation').sum()):,}, "
      f"other zero-value {int(((df.channel != 'Reclamation') & (df.order_total <= 0)).sum()):,})")

g = s.groupby("channel", observed=True)
t = pd.DataFrame({
    "orders": g.size(),
    "revenue_tnd": g["order_total"].sum(),
    "mean_basket": g["order_total"].mean(),
    "median_basket": g["order_total"].median(),
    "p25_basket": g["order_total"].quantile(0.25),
    "p75_basket": g["order_total"].quantile(0.75),
    "customers": g["customer_id"].nunique(),
    # share of the channel's orders at its single most common exact basket value:
    # a high value means one product/offer dominates and distorts the median
    "top_price_share_pct": g["order_total"].agg(lambda x: 100 * x.round(2).value_counts(normalize=True).iloc[0]),
}).reindex(CHANNELS)
t.insert(1, "share_orders_pct", 100 * t["orders"] / t["orders"].sum())
t.insert(3, "share_revenue_pct", 100 * t["revenue_tnd"] / t["revenue_tnd"].sum())

total = pd.DataFrame({
    "orders": [len(s)], "share_orders_pct": [100.0], "revenue_tnd": [s.order_total.sum()],
    "share_revenue_pct": [100.0], "mean_basket": [s.order_total.mean()],
    "median_basket": [s.order_total.median()], "p25_basket": [s.order_total.quantile(.25)],
    "p75_basket": [s.order_total.quantile(.75)], "customers": [s.customer_id.nunique()],
    "top_price_share_pct": [100 * s.order_total.round(2).value_counts(normalize=True).iloc[0]],
}, index=["All sales"])
t = pd.concat([t, total]).rename_axis("channel").reset_index()
ROUND = {"share_orders_pct": 2, "share_revenue_pct": 2, "revenue_tnd": 0, "mean_basket": 1,
         "median_basket": 1, "p25_basket": 1, "p75_basket": 1, "top_price_share_pct": 1}
t = t.round(ROUND)
t["revenue_tnd"] = t["revenue_tnd"].astype("int64")

# Instagram side table: the two raw codes the company groups as "Instagram"
ig = s[s["channel"] == "Instagram"].groupby("source_code", observed=True)["order_total"]
sub = pd.DataFrame({
    "orders": ig.size(), "revenue_tnd": ig.sum(), "mean_basket": ig.mean(),
    "median_basket": ig.median(), "p25_basket": ig.quantile(.25), "p75_basket": ig.quantile(.75),
    "top_price_share_pct": ig.agg(lambda x: 100 * x.round(2).value_counts(normalize=True).iloc[0]),
    "top3_prices_share_pct": ig.agg(lambda x: 100 * x.round(2).value_counts(normalize=True).head(3).sum()),
}).rename(index={"0": "Instagram page (code 0)", "Instagram": "Instagram (code 'Instagram')"})
sub = sub.rename_axis("instagram_code").reset_index().round({**ROUND, "top3_prices_share_pct": 1})
sub["revenue_tnd"] = sub["revenue_tnd"].astype("int64")

p1 = save_table(t, "01_channel_performance")
p2 = save_table(sub, "01b_instagram_codes")
with pd.option_context("display.width", 250):
    print(t.to_string(index=False))
    print("\n" + sub.to_string(index=False))
print(f"\nSaved {p1.name}, {p2.name} in outputs/tables/")
