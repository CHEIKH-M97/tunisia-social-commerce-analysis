"""Analysis 6 (optional) - ESTIMATED gender split from first names.

gender_est comes from a first-name dictionary + manual labels (see src/names.py).
It is a rough estimate: "unknown" covers unmatched or unisex names, and the
name on an order may be the recipient's rather than the buyer's.
For every group we report:
  coverage_pct      share of orders with an F/M estimate
  female_of_known   F / (F + M)
  female_floor_pct  F / all orders = female share if EVERY unknown were male
Customer-level gender = majority estimate over the customer's labelled orders;
exact F/M ties are "mixed".
Scope: sales only.
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.common import CHANNELS, load, region, sales, save_table  # noqa: E402

s = sales(load())
for c in ["channel", "governorate", "gender_est"]:
    s[c] = s[c].astype(str)
s["region"] = s["governorate"].map(region)


def split(df: pd.DataFrame, by: str | None) -> pd.DataFrame:
    keys = [by] if by else []
    ct = (df.groupby(keys + ["gender_est"]).size().unstack(fill_value=0)
          if by else df["gender_est"].value_counts().to_frame().T)
    ct = ct.reindex(columns=["F", "M", "unknown"], fill_value=0)
    out = pd.DataFrame({"orders": ct.sum(axis=1), "F_orders": ct["F"], "M_orders": ct["M"],
                        "unknown_orders": ct["unknown"]})
    out["coverage_pct"] = 100 * (out.F_orders + out.M_orders) / out.orders
    out["female_of_known_pct"] = 100 * out.F_orders / (out.F_orders + out.M_orders)
    out["female_floor_pct"] = 100 * out.F_orders / out.orders
    return out.round(2)


overall = split(s, None)
overall.index = ["All sales"]
overall = overall.rename_axis("group").reset_index()

ch = split(s[s.channel != "Unknown"], "channel").reindex([c for c in CHANNELS if c != "Unknown"])
ch = ch.rename_axis("channel").reset_index()

sg = s[s.governorate != "Unknown"]
rg = split(sg, "region").rename_axis("region").reset_index()
gv = split(sg, "governorate").sort_values("female_of_known_pct", ascending=False)
gv.insert(0, "region", [region(x) for x in gv.index])
gv = gv.rename_axis("governorate").reset_index()

# ---- behaviour by customer-level estimated gender
# Majority vote over the customer's labelled orders (ties -> "mixed"). A strict
# "all orders agree" rule was tried first and rejected: a man with one order
# under a woman's name (e.g. a gift) left the M group, so M filled up with
# one-time buyers and the repeat-rate gap was overstated.
k = s[s.gender_est != "unknown"].groupby(["customer_id", "gender_est"]).size().unstack(fill_value=0)
lab = pd.Series("mixed", index=k.index)
lab[k["F"] > k["M"]] = "F"
lab[k["M"] > k["F"]] = "M"
cust = s.groupby("customer_id").agg(orders=("order_total", "size"), revenue=("order_total", "sum"))
cust["gender_cust"] = lab.reindex(cust.index).fillna("unknown")
s = s.join(cust["gender_cust"], on="customer_id")
beh = cust.groupby("gender_cust").agg(customers=("orders", "size"), orders=("orders", "sum"),
                                      repeat_rate_pct=("orders", lambda x: 100 * (x > 1).mean()),
                                      orders_per_customer=("orders", "mean"),
                                      revenue_per_customer_tnd=("revenue", "mean"))
bk = s.groupby("gender_cust")["order_total"]
beh["median_basket"] = bk.median()
beh["mean_basket"] = bk.mean()
beh["share_120plus_pct"] = s.assign(b=s.order_total >= 120).groupby("gender_cust")["b"].mean() * 100
beh["share_customers_pct"] = 100 * beh["customers"] / beh["customers"].sum()
beh = beh.reindex(["F", "M", "mixed", "unknown"]).rename_axis("gender_est_customer").reset_index().round(2)

paths = [save_table(overall, "06_gender_estimated_overall"),
         save_table(ch, "06b_gender_estimated_by_channel"),
         save_table(rg, "06c_gender_estimated_coastal_interior"),
         save_table(gv, "06d_gender_estimated_by_governorate"),
         save_table(beh, "06e_gender_estimated_behaviour")]
for t in [ch, gv]:  # every M cell must also respect the publication rule
    assert (t["M_orders"] >= 50).all() and (t["F_orders"] >= 50).all()
with pd.option_context("display.width", 250, "display.max_columns", 30):
    for t in [overall, ch, rg, gv, beh]:
        print("\n" + t.to_string(index=False))
print("\nSaved " + ", ".join(p.name for p in paths))
