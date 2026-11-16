"""Analysis 4 - repeat customers and revenue concentration.

Customer = hashed phone. Repeat customer = 2+ sales orders.
- Orders-per-customer buckets, revenue concentration (top 1/5/10/20%).
- Repeat rate by channel: among customers who bought on a channel, share who
  bought on that same channel 2+ times (no dates exist, so "first channel"
  cannot be known).
- Repeat rate by governorate: each customer assigned to the governorate that
  received most of their orders.
Scope: sales only (Reclamation and zero-value orders excluded).
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.common import CHANNELS, load, region, sales, save_table  # noqa: E402

s = sales(load())
s["channel"] = s["channel"].astype(str)
s["governorate"] = s["governorate"].astype(str)

cust = s.groupby("customer_id").agg(orders=("order_total", "size"), revenue=("order_total", "sum"),
                                    channels=("channel", "nunique"))
n_c = len(cust)
print(f"Sales orders {len(s):,} | customers {n_c:,} | repeat rate {100 * (cust.orders > 1).mean():.1f}% | "
      f"customers using 2+ channels {100 * (cust.channels > 1).mean():.1f}%")

# ---- 1. orders-per-customer buckets
bins, labels = [0, 1, 2, 5, 10, np.inf], ["1 order", "2 orders", "3-5 orders", "6-10 orders", "11+ orders"]
cust["bucket"] = pd.cut(cust["orders"], bins=bins, labels=labels)
s = s.join(cust["bucket"], on="customer_id")
b = cust.groupby("bucket", observed=True).agg(customers=("orders", "size"), orders=("orders", "sum"),
                                               revenue=("revenue", "sum"))
b["median_basket"] = s.groupby("bucket", observed=True)["order_total"].median()
b["share_customers_pct"] = 100 * b["customers"] / n_c
b["share_orders_pct"] = 100 * b["orders"] / b["orders"].sum()
b["share_revenue_pct"] = 100 * b["revenue"] / b["revenue"].sum()
b = b.drop(columns="revenue").rename_axis("bucket").reset_index().round(2)

# ---- 2. revenue concentration
cs = cust.sort_values("revenue", ascending=False)
rows = []
for p in [1, 5, 10, 20, 50]:
    top = cs.head(int(round(n_c * p / 100)))
    rows.append({"top_customers_pct": p, "customers": len(top), "orders": int(top.orders.sum()),
                 "share_revenue_pct": 100 * top.revenue.sum() / cs.revenue.sum(),
                 "min_revenue_tnd_in_group": top.revenue.min(), "avg_orders_per_customer": top.orders.mean()})
conc = pd.DataFrame(rows).round(2)

# ---- 3. repeat rate by channel (within-channel)
cc = s.groupby(["channel", "customer_id"]).size().rename("n").reset_index()
ch = cc.groupby("channel").agg(customers=("n", "size"), repeat_customers=("n", lambda x: int((x > 1).sum())),
                               orders=("n", "sum"))
ch["repeat_rate_pct"] = 100 * ch["repeat_customers"] / ch["customers"]
ch["orders_per_customer"] = ch["orders"] / ch["customers"]
ch = ch.reindex(CHANNELS).rename_axis("channel").reset_index().round(2)

# ---- 3b. robustness: customers who used ONE channel only (removes the volume effect)
cust_ch = s.groupby("customer_id")["channel"].agg(["nunique", "first"])
one = cust[cust_ch["nunique"] == 1].join(cust_ch["first"].rename("channel"))
sc = one.groupby("channel").agg(customers=("orders", "size"), orders=("orders", "sum"),
                                repeat_customers=("orders", lambda x: int((x > 1).sum())))
sc["repeat_rate_pct"] = 100 * sc["repeat_customers"] / sc["customers"]
sc["orders_per_customer"] = sc["orders"] / sc["customers"]
multi = cust[cust_ch["nunique"] > 1]
sc.loc["Multi-channel customers"] = [len(multi), multi.orders.sum(), int((multi.orders > 1).sum()),
                                     100 * (multi.orders > 1).mean(), multi.orders.mean()]
sc["share_customers_pct"] = 100 * sc["customers"] / n_c
sc["share_revenue_pct"] = pd.concat([one.groupby("channel")["revenue"].sum(),
                                     pd.Series({"Multi-channel customers": multi.revenue.sum()})]) / cust.revenue.sum() * 100
sc = sc.reindex(CHANNELS + ["Multi-channel customers"]).rename_axis("customer_group").reset_index().round(2)
sc[["customers", "orders", "repeat_customers"]] = sc[["customers", "orders", "repeat_customers"]].astype("int64")

# ---- 4. repeat rate by main governorate
main_gov = (s.groupby(["customer_id", "governorate"]).size().rename("n").reset_index()
            .sort_values(["customer_id", "n", "governorate"], ascending=[True, False, True])
            .drop_duplicates("customer_id").set_index("customer_id")["governorate"])
cust["governorate"] = main_gov
cg = cust[cust["governorate"] != "Unknown"]
gv = cg.groupby("governorate").agg(customers=("orders", "size"), orders=("orders", "sum"),
                                    repeat_customers=("orders", lambda x: int((x > 1).sum())),
                                    revenue=("revenue", "sum"))
gv["repeat_rate_pct"] = 100 * gv["repeat_customers"] / gv["customers"]
gv["orders_per_customer"] = gv["orders"] / gv["customers"]
gv["revenue_per_customer_tnd"] = gv["revenue"] / gv["customers"]
gv["region"] = [region(g) for g in gv.index]
reg = cg.assign(region=cg["governorate"].map(region)).groupby("region").agg(
    customers=("orders", "size"), orders=("orders", "sum"),
    repeat_customers=("orders", lambda x: int((x > 1).sum())), revenue=("revenue", "sum"))
reg["repeat_rate_pct"] = 100 * reg["repeat_customers"] / reg["customers"]
reg["orders_per_customer"] = reg["orders"] / reg["customers"]
reg["revenue_per_customer_tnd"] = reg["revenue"] / reg["customers"]
reg["region"] = reg.index + " (all)"
gv = pd.concat([gv.sort_values("repeat_rate_pct", ascending=False), reg]).drop(columns="revenue")
gv = gv.rename_axis("governorate").reset_index()
gv.loc[gv["governorate"].isin(["Coastal", "Interior"]), "governorate"] = "ALL"
gv = gv[["governorate", "region", "customers", "repeat_customers", "repeat_rate_pct", "orders",
         "orders_per_customer", "revenue_per_customer_tnd"]].round(2)

paths = [save_table(b, "04_orders_per_customer"), save_table(conc, "04b_revenue_concentration"),
         save_table(ch, "04c_repeat_by_channel"), save_table(gv, "04d_repeat_by_governorate"),
         save_table(sc, "04e_repeat_single_channel_customers")]
with pd.option_context("display.width", 250, "display.max_columns", 30):
    for t in [b, conc, ch, gv, sc]:
        print("\n" + t.to_string(index=False))
print("\nSaved " + ", ".join(p.name for p in paths))
