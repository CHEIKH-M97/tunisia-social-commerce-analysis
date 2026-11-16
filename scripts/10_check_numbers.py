"""Fact-check: every number quoted in the README, the carousel text and the
LinkedIn post, compared with the published tables.

Each claim = (where, text as written, value as written, value from tables).
A claim passes if the written value equals the table value rounded to the
same number of decimals (half a unit of the last shown digit, + float slack).
"""
import sys
from pathlib import Path

import pandas as pd

T = Path(__file__).resolve().parents[1] / "outputs" / "tables"
read = lambda n: pd.read_csv(T / f"{n}.csv")  # noqa: E731

ch = read("01_channel_performance").set_index("channel")
ig = read("01b_instagram_codes").set_index("instagram_code")
geo = read("02_geography_governorates").set_index("governorate")
cr = read("02b_coastal_vs_interior").set_index("region")
mix = read("03b_channel_mix_by_governorate").set_index("governorate")
mcr = read("03c_channel_mix_coastal_interior").set_index("region")
bk = read("04_orders_per_customer").set_index("bucket")
conc = read("04b_revenue_concentration").set_index("top_customers_pct")
rp = read("04d_repeat_by_governorate")
rp = rp[rp.governorate == "ALL"].set_index("region")
sc = read("04e_repeat_single_channel_customers").set_index("customer_group")
pb = read("05_price_bands_overall").set_index("band")
bkr = read("05c_basket_coastal_interior").set_index("region")
ge = read("06_gender_estimated_overall").iloc[0]
gb = read("06e_gender_estimated_behaviour").set_index("gender_est_customer")

coast_gap = 100 * (cr.loc["Coastal", "customers_per_1000"] / cr.loc["Interior", "customers_per_1000"] - 1)
orders_gap = 100 * (cr.loc["Coastal", "orders_per_1000"] / cr.loc["Interior", "orders_per_1000"] - 1)
fb_r = mix["Facebook Page %"].corr(geo["orders_per_1000"])
big = pb.loc[["120-200", "200+"]].sum()

# Facts available for claims: name -> value from tables
F = {
    "tiktok_orders": ch.loc["TikTok Live", "share_orders_pct"],
    "tiktok_revenue": ch.loc["TikTok Live", "share_revenue_pct"],
    "fb_orders": ch.loc["Facebook Page", "share_orders_pct"],
    "ig_orders": ch.loc["Instagram", "share_orders_pct"],
    "web_orders": ch.loc["Website (Shopify)", "share_orders_pct"],
    "meta_orders": ch.loc["Facebook Page", "share_orders_pct"] + ch.loc["Instagram", "share_orders_pct"],
    "ig_code_top3": ig.loc["Instagram (code 'Instagram')", "top3_prices_share_pct"],
    "sales_orders": ch.loc["All sales", "orders"],
    "sales_customers": ch.loc["All sales", "customers"],
    "median_basket": ch.loc["All sales", "median_basket"],
    "tt_repeat_single": sc.loc["TikTok Live", "repeat_rate_pct"],
    "fb_repeat_single": sc.loc["Facebook Page", "repeat_rate_pct"],
    "ig_repeat_single": sc.loc["Instagram", "repeat_rate_pct"],
    "tt_fb_ratio": sc.loc["TikTok Live", "repeat_rate_pct"] / sc.loc["Facebook Page", "repeat_rate_pct"],
    "multi_customers": sc.loc["Multi-channel customers", "share_customers_pct"],
    "multi_revenue": sc.loc["Multi-channel customers", "share_revenue_pct"],
    "repeat_customers": 100 - bk.loc["1 order", "share_customers_pct"],
    "repeat_revenue": 100 - bk.loc["1 order", "share_revenue_pct"],
    "top10_revenue": conc.loc[10, "share_revenue_pct"],
    "top1_revenue": conc.loc[1, "share_revenue_pct"],
    "coast_cust_gap": coast_gap,
    "coast_orders_gap": orders_gap,
    "coast_cust_1000": cr.loc["Coastal", "customers_per_1000"],
    "int_cust_1000": cr.loc["Interior", "customers_per_1000"],
    "coast_repeat": rp.loc["Coastal (all)", "repeat_rate_pct"],
    "int_repeat": rp.loc["Interior (all)", "repeat_rate_pct"],
    "coast_mean_basket": bkr.loc["Coastal", "mean"],
    "int_mean_basket": bkr.loc["Interior", "mean"],
    "tt_min_gov": mix["TikTok Live %"].min(),
    "tt_max_gov": mix["TikTok Live %"].max(),
    "fb_coastal": mcr.loc["Coastal", "Facebook Page %"],
    "fb_interior": mcr.loc["Interior", "Facebook Page %"],
    "fb_reach_r": fb_r,
    "big_orders": big["share_orders_pct"],
    "big_revenue": big["share_revenue_pct"],
    "under50_orders": pb.loc["30-50", "cum_share_orders_pct"],
    "female_known": ge["female_of_known_pct"],
    "female_floor": ge["female_floor_pct"],
    "gender_coverage": ge["coverage_pct"],
    "f_repeat": gb.loc["F", "repeat_rate_pct"],
    "m_repeat": gb.loc["M", "repeat_rate_pct"],
    "nat_orders_1000": 1000 * geo["orders"].sum() / geo["population_2024"].sum(),
    "top_gov_1000": geo["orders_per_1000"].max(),
    "bottom_gov_1000": geo["orders_per_1000"].min(),
}

# Claims: (document, text, written value, fact name)
CLAIMS = [
    ("README", "TikTok Live 64.1% of orders", 64.1, "tiktok_orders"),
    ("README", "TikTok Live 63.5% of revenue", 63.5, "tiktok_revenue"),
    ("README", "Facebook Page 24.6%", 24.6, "fb_orders"),
    ("README", "Instagram 9.9%", 9.9, "ig_orders"),
    ("README", "website 0.3%", 0.3, "web_orders"),
    ("README", "single-channel repeat TikTok 35.3%", 35.3, "tt_repeat_single"),
    ("README", "single-channel repeat Facebook 19.8%", 19.8, "fb_repeat_single"),
    ("README", "single-channel repeat Instagram 13.9%", 13.9, "ig_repeat_single"),
    ("README", "43.1% of customers ordered more than once", 43.1, "repeat_customers"),
    ("README", "repeat customers = 77.7% of revenue", 77.7, "repeat_revenue"),
    ("README", "top 10% of customers = 45.1%", 45.1, "top10_revenue"),
    ("README", "38% more customers per inhabitant", 38, "coast_cust_gap"),
    ("README", "57.6 customers per 1,000 coastal", 57.6, "coast_cust_1000"),
    ("README", "41.9 customers per 1,000 interior", 41.9, "int_cust_1000"),
    ("README", "repeat rate coastal 43.0%", 43.0, "coast_repeat"),
    ("README", "repeat rate interior 43.4%", 43.4, "int_repeat"),
    ("README", "average order coastal 78.8", 78.8, "coast_mean_basket"),
    ("README", "average order interior 79.8", 79.8, "int_mean_basket"),
    ("README", "TikTok min share by governorate 58.3%", 58.3, "tt_min_gov"),
    ("README", "TikTok max share by governorate 68.6%", 68.6, "tt_max_gov"),
    ("README", "Facebook 23.8% coastal", 23.8, "fb_coastal"),
    ("README", "Facebook 28.1% interior", 28.1, "fb_interior"),
    ("README", "r = -0.69", -0.69, "fb_reach_r"),
    ("README", "120+ TND = 15.3% of orders", 15.3, "big_orders"),
    ("README", "120+ TND = 37.8% of revenue", 37.8, "big_revenue"),
    ("README", "39.8% of orders under 50 TND", 39.8, "under50_orders"),
    ("README", "median order 62.8 TND", 62.8, "median_basket"),
    ("README", "95.9% women's names among classifiable", 95.9, "female_known"),
    ("README", "82.1% worst-case floor", 82.1, "female_floor"),
    ("README", "gender coverage 85.7%", 85.7, "gender_coverage"),
    ("README", "1,494,712 sales orders", 1494712, "sales_orders"),
    ("README", "623,661 customers", 623661, "sales_customers"),
    ("README", "57% of orders under one Instagram code at three prices", 57, "ig_code_top3"),
    ("Carousel", "cover: 64% of orders from TikTok Live", 64, "tiktok_orders"),
    ("Carousel", "cover: 78% of revenue from repeat customers", 78, "repeat_revenue"),
    ("Carousel", "cover: +38% buyers per inhabitant on the coast", 38, "coast_cust_gap"),
    ("Carousel", "cover: 1.5 million orders", 1.5e6, "sales_orders"),
    ("Carousel", "tip 1: come back 1.8x as often", 1.8, "tt_fb_ratio"),
    ("Carousel", "tip 2: repeat buyers 43% of customers", 43, "repeat_customers"),
    ("Carousel", "tip 2: top 10% bring 45%", 45, "top10_revenue"),
    ("Carousel", "tip 5: 120 TND+ = 15% of orders", 15, "big_orders"),
    ("Carousel", "tip 5: 120 TND+ = 38% of revenue", 38, "big_revenue"),
    ("LinkedIn", "1.5 million social-commerce orders", 1.5e6, "sales_orders"),
    ("LinkedIn", "TikTok Live brought 64% of orders", 64, "tiktok_orders"),
    ("LinkedIn", "Facebook Page 25%", 25, "fb_orders"),
    ("LinkedIn", "Instagram 10%", 10, "ig_orders"),
    ("LinkedIn", "website 0.3%", 0.3, "web_orders"),
    ("LinkedIn", "TikTok 35% ordered again (single-channel)", 35, "tt_repeat_single"),
    ("LinkedIn", "vs 20% on the Facebook Page", 20, "fb_repeat_single"),
    ("LinkedIn", "'almost twice as often' (ratio, 1 sig. digit -> ~2)", 2, "tt_fb_ratio"),
    ("LinkedIn", "repeat customers 43% of buyers", 43, "repeat_customers"),
    ("LinkedIn", "repeat customers 78% of revenue", 78, "repeat_revenue"),
    ("LinkedIn", "top 10% brought 45%", 45, "top10_revenue"),
    ("LinkedIn", "coast 38% more buyers per inhabitant", 38, "coast_cust_gap"),
    ("LinkedIn", "120 TND+ = 15% of orders", 15, "big_orders"),
    ("LinkedIn", "120 TND+ = 38% of revenue", 38, "big_revenue"),
    ("LinkedIn", "at least 8 in 10 orders: woman's name (floor >= 80%)", 82, "female_floor"),
    ("LinkedIn", "the real repeat figure is 43%", 43, "repeat_customers"),
]
# Qualitative claims checked as inequalities: (document, text, condition)
CONDITIONS = [
    ("LinkedIn", "'almost twice as often': ratio between 1.7 and 2.0", 1.7 <= F["tt_fb_ratio"] < 2.0),
    ("LinkedIn", "'at least 8 in 10': worst-case floor >= 80%", F["female_floor"] >= 80),
    ("LinkedIn", "'interior spends the same': mean basket gap < 2%",
     abs(F["int_mean_basket"] / F["coast_mean_basket"] - 1) < 0.02),
    ("LinkedIn", "'come back just as often': repeat gap < 1 pt", abs(F["int_repeat"] - F["coast_repeat"]) < 1),
    ("Carousel", "'Two out of three orders': TikTok share 60-70%", 60 <= F["tiktok_orders"] < 70),
    ("Carousel", "'almost 8 dinars out of 10': 75-80%", 75 <= F["repeat_revenue"] < 80),
]


def decimals(x: float) -> int:
    s = repr(float(x)).rstrip("0").rstrip(".")
    return len(s.split(".")[1]) if "." in s else 0


def check(claims) -> bool:
    ok = True
    for doc, text, written, fact in claims:
        true = F[fact]
        if written >= 1e5 and written % 1e5 == 0 and true % 1 == 0 and written != true:  # "1.5 million"
            tol = 0.05e6
        else:
            tol = 0.5 * 10 ** -decimals(written) + 1e-9
        good = abs(written - true) <= tol
        ok &= good
        print(f"  {'OK  ' if good else 'FAIL'}  [{doc}] {text:55s} written {written:<10g} table {true:.4f}")
    return ok


if __name__ == "__main__":
    passed = check([c for c in CLAIMS if c[3] != "tt_fb_ratio" or c[2] != 2])  # ratio "~2" checked below
    for doc, text, cond in CONDITIONS:
        passed &= bool(cond)
        print(f"  {'OK  ' if cond else 'FAIL'}  [{doc}] {text}")
    print("\nALL CLAIMS MATCH THE TABLES" if passed else "\nSOME CLAIMS DO NOT MATCH - fix before publishing")
    sys.exit(0 if passed else 1)
