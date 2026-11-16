"""Analysis 3 - which channel dominates where.

Channel mix (share of orders) per governorate and for coastal vs interior.
"index" = the channel's local share / its national share x 100, so 120 means
the channel is 20% more important there than nationally.
Scope: sales, known governorate, known channel. Cells under MIN_N orders are
suppressed (blank) before publication.
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.common import CHANNELS, MIN_N, load, region, sales, save_table  # noqa: E402

s = sales(load())
s = s[(s["governorate"] != "Unknown") & (s["channel"] != "Unknown")].copy()
s["governorate"] = s["governorate"].astype(str)
s["channel"] = s["channel"].astype(str)
s["region"] = s["governorate"].map(region)
chans = [c for c in CHANNELS if c != "Unknown"]
print(f"Scope: {len(s):,} sales orders with known governorate and channel")

national = s["channel"].value_counts(normalize=True).reindex(chans) * 100

# ---- long table: one row per governorate x channel
ct = pd.crosstab(s["governorate"], s["channel"]).reindex(columns=chans, fill_value=0)
share = ct.div(ct.sum(axis=1), axis=0) * 100
long = (ct.stack().rename("orders").to_frame()
        .join(share.stack().rename("share_of_gov_orders_pct")).reset_index())
long["index_vs_national"] = 100 * long["share_of_gov_orders_pct"] / long["channel"].map(national)
long["region"] = long["governorate"].map(region)
n_supp = int((long["orders"] < MIN_N).sum())
long = long[long["orders"] >= MIN_N]
long = long[["governorate", "region", "channel", "orders", "share_of_gov_orders_pct", "index_vs_national"]]
long = long.round({"share_of_gov_orders_pct": 2, "index_vs_national": 0})

# ---- wide table: shares per governorate, suppressed cells blank
wide = share.where(ct >= MIN_N).round(2)
wide.columns = [f"{c} %" for c in wide.columns]
wide.insert(0, "orders", ct.sum(axis=1))
wide.insert(0, "region", [region(g) for g in wide.index])
wide["dominant_channel"] = share.idxmax(axis=1)
wide["tiktok_index"] = (100 * share["TikTok Live"] / national["TikTok Live"]).round(0)
wide["facebook_index"] = (100 * share["Facebook Page"] / national["Facebook Page"]).round(0)
wide["instagram_index"] = (100 * share["Instagram"] / national["Instagram"]).round(0)
wide = wide.sort_values("TikTok Live %", ascending=False).rename_axis("governorate").reset_index()

# ---- coastal vs interior
rc = pd.crosstab(s["region"], s["channel"]).reindex(columns=chans)
rs = (rc.div(rc.sum(axis=1), axis=0) * 100).round(2)
rs.columns = [f"{c} %" for c in rs.columns]
rs.insert(0, "orders", rc.sum(axis=1))
rs = rs.rename_axis("region").reset_index()
assert (rc >= MIN_N).all().all()

p1 = save_table(long, "03_channel_by_governorate_long")
p2 = save_table(wide, "03b_channel_mix_by_governorate")
p3 = save_table(rs, "03c_channel_mix_coastal_interior")
with pd.option_context("display.width", 250, "display.max_columns", 30):
    print("National mix %: " + ", ".join(f"{k} {v:.2f}" for k, v in national.items()))
    print(f"Cells suppressed (< {MIN_N} orders): {n_supp}\n")
    print(wide.to_string(index=False))
    print("\n" + rs.to_string(index=False))
print(f"\nSaved {p1.name}, {p2.name}, {p3.name}")
