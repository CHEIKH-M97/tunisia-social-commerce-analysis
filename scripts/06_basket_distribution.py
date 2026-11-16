"""Analysis 5 - basket distribution.

order_total is the product price of the order (no delivery fees).
Price bands (TND): <30, 30-50, 50-80, 80-120, 120-200, 200+.
Breakdowns: overall, by channel, coastal vs interior, by governorate.
Scope: sales only. Unknown channel / governorate excluded from their breakdowns.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.common import CHANNELS, load, region, sales, save_table  # noqa: E402

BINS = [0, 30, 50, 80, 120, 200, np.inf]
BANDS = ["<30", "30-50", "50-80", "80-120", "120-200", "200+"]

s = sales(load())
s["channel"] = s["channel"].astype(str)
s["governorate"] = s["governorate"].astype(str)
s["region"] = s["governorate"].map(region)
s["band"] = pd.cut(s["order_total"], bins=BINS, labels=BANDS, right=False)


def stats(g: pd.core.groupby.DataFrameGroupBy) -> pd.DataFrame:
    x = g["order_total"]
    return pd.DataFrame({"orders": x.size(), "p10": x.quantile(.10), "p25": x.quantile(.25),
                         "median": x.median(), "p75": x.quantile(.75), "p90": x.quantile(.90),
                         "mean": x.mean()})


def band_shares(df: pd.DataFrame, by: str) -> pd.DataFrame:
    ct = pd.crosstab(df[by], df["band"]).reindex(columns=BANDS, fill_value=0)
    sh = ct.div(ct.sum(axis=1), axis=0) * 100
    sh.columns = [f"{c} %" for c in sh.columns]
    return sh, ct


# ---- overall
o = s.groupby("band", observed=False).agg(orders=("order_total", "size"), revenue=("order_total", "sum"))
o["share_orders_pct"] = 100 * o["orders"] / o["orders"].sum()
o["share_revenue_pct"] = 100 * o["revenue"] / o["revenue"].sum()
o["cum_share_orders_pct"] = o["share_orders_pct"].cumsum()
o = o.drop(columns="revenue").rename_axis("band").reset_index().round(2)

# ---- by channel
sc = s[s["channel"] != "Unknown"]
ch_sh, ch_ct = band_shares(sc, "channel")
ch = stats(sc.groupby("channel")).join(ch_sh).reindex([c for c in CHANNELS if c != "Unknown"])
assert (ch_ct >= 50).all().all(), "small channel x band cell"
ch = ch.rename_axis("channel").reset_index().round(2)

# ---- coastal vs interior
sg = s[s["governorate"] != "Unknown"]
r_sh, _ = band_shares(sg, "region")
rg = stats(sg.groupby("region")).join(r_sh).rename_axis("region").reset_index().round(2)

# ---- by governorate
g_sh, g_ct = band_shares(sg, "governorate")
assert (g_ct >= 50).all().all(), "small governorate x band cell"
gv = stats(sg.groupby("governorate")).join(g_sh)
gv.insert(0, "region", [region(x) for x in gv.index])
gv["120+ %"] = gv["120-200 %"] + gv["200+ %"]
gv = gv.sort_values("mean", ascending=False).rename_axis("governorate").reset_index().round(2)

paths = [save_table(o, "05_price_bands_overall"), save_table(ch, "05b_basket_by_channel"),
         save_table(rg, "05c_basket_coastal_interior"), save_table(gv, "05d_basket_by_governorate")]
with pd.option_context("display.width", 260, "display.max_columns", 30):
    for t in [o, ch, rg, gv]:
        print("\n" + t.to_string(index=False))
print("\nSaved " + ", ".join(p.name for p in paths))
