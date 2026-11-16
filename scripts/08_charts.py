"""Phase 3 - one chart per key finding. Reads ONLY the published tables."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.style import (ACCENT, AXIS, COASTAL, GRID, INK, INK2, INTERIOR, MUTED, NEUTRAL,  # noqa: E402
                       SURFACE, clean_hbar, figure, save)

T = Path(__file__).resolve().parents[1] / "outputs" / "tables"
read = lambda name: pd.read_csv(T / f"{name}.csv")  # noqa: E731
out = []


def pct(v, d=0):
    return f"{v:.{d}f}%"


# ---------------------------------------------------------------- 1. channel mix
ch = read("01_channel_performance").set_index("channel")
names = ["TikTok Live", "Facebook Page", "Instagram", "Website (Shopify)"]
vals = ch.loc[names, "share_orders_pct"]
fig, ax = figure("Two out of three orders come from TikTok Live",
                 f"Share of sales orders by channel. Revenue follows the same split "
                 f"(TikTok Live: {ch.loc['TikTok Live', 'share_revenue_pct']:.1f}% of revenue).",
                 note=f"{ch.loc['Unknown', 'share_orders_pct']:.1f}% of orders with no recorded channel not shown.",
                 plot_box=(0.30, 0.14, 0.60, 0.58))
y = np.arange(len(names))[::-1]
ax.barh(y, vals, height=0.62, color=[ACCENT] + [NEUTRAL] * 3)
for yi, v in zip(y, vals):
    ax.text(v + 1.2, yi, pct(v, 1), va="center", fontsize=12, fontweight="bold" if v > 50 else "normal",
            color=INK if v > 50 else INK2)
ax.set_yticks(y, ["TikTok Live", "Facebook Page", "Instagram", "Website"])
ax.set_xlim(0, 80)
clean_hbar(ax)
out.append(save(fig, "01_channel_mix"))

# ---------------------------------------------------------------- 2. repeat customers
b = read("04_orders_per_customer").set_index("bucket")
conc = read("04b_revenue_concentration").set_index("top_customers_pct")
one_c, one_r = b.loc["1 order", "share_customers_pct"], b.loc["1 order", "share_revenue_pct"]
fig, ax = figure("Repeat customers bring in almost 8 dinars out of 10",
                 f"{100 - one_c:.0f}% of customers ordered more than once. "
                 f"Together they account for {100 - one_r:.0f}% of revenue.",
                 note="Customer = anonymized phone number.", plot_box=(0.08, 0.30, 0.86, 0.36))
rows = [("Customers", one_c), ("Revenue", one_r)]
for i, (lab, one) in enumerate(rows):
    yy = 1 - i
    ax.barh(yy, one, height=0.55, color=NEUTRAL, edgecolor=SURFACE, linewidth=2)
    ax.barh(yy, 100 - one, left=one, height=0.55, color=ACCENT, edgecolor=SURFACE, linewidth=2)
    ax.text(one / 2, yy, f"One-time\n{one:.0f}%", ha="center", va="center", fontsize=10.5, color=INK)
    ax.text(one + (100 - one) / 2, yy, f"Repeat\n{100 - one:.0f}%", ha="center", va="center",
            fontsize=10.5, color="white", fontweight="bold")
    ax.text(0, yy + 0.38, lab, fontsize=10.5, color=INK2, va="bottom")
ax.set_xlim(0, 100)
ax.set_ylim(-0.5, 1.75)
ax.axis("off")
top10 = conc.loc[10, "share_revenue_pct"]
fig.text(0.08, 0.235, f"{top10:.0f}%", fontsize=34, fontweight="bold", color=ACCENT, va="top")
fig.text(0.33, 0.228, "of revenue comes from the\ntop 10% of customers", fontsize=11, color=INK,
         va="top", linespacing=1.3)
out.append(save(fig, "02_repeat_customers"))

# ---------------------------------------------------------------- 3. TikTok loyalty
sc = read("04e_repeat_single_channel_customers").set_index("customer_group")
names = ["TikTok Live", "Facebook Page", "Instagram"]
vals = sc.loc[names, "repeat_rate_pct"]
ratio = vals["TikTok Live"] / vals["Facebook Page"]
fig, ax = figure("TikTok Live buyers come back almost twice as often",
                 "Share of customers who ordered again, among customers who only ever "
                 "used that one channel.",
                 note=f"Single-channel customers: {int(sc.loc[names, 'customers'].sum()):,}. "
                      f"Website excluded (only {int(sc.loc['Website (Shopify)', 'customers']):,} customers).",
                 plot_box=(0.30, 0.19, 0.60, 0.52))
y = np.arange(len(names))[::-1]
ax.barh(y, vals, height=0.6, color=[ACCENT, NEUTRAL, NEUTRAL])
for yi, v in zip(y, vals):
    ax.text(v + 0.8, yi, pct(v), va="center", fontsize=13, fontweight="bold" if v > 30 else "normal",
            color=INK if v > 30 else INK2)
ax.set_yticks(y, names)
ax.set_xlim(0, 45)
clean_hbar(ax)
fig.text(0.30, 0.135, f"{ratio:.1f}x the Facebook Page repeat rate", fontsize=9.5, color=INK2)
out.append(save(fig, "03_tiktok_loyalty"))

# ---------------------------------------------------------------- 4. reach, not spending
cr = read("02b_coastal_vs_interior").set_index("region")
rp = read("04d_repeat_by_governorate")
rp = rp[rp["governorate"] == "ALL"].assign(region=lambda d: d["region"].str.replace(" (all)", "", regex=False)).set_index("region")
bk = read("05c_basket_coastal_interior").set_index("region")
panels = [("Customers per\n1,000 inhabitants", cr["customers_per_1000"], "{:.0f}"),
          ("Customers who\nordered again", rp["repeat_rate_pct"], "{:.0f}%"),
          ("Average order\n(TND)", bk["mean"], "{:.0f}")]
gap = 100 * (cr.loc["Coastal", "customers_per_1000"] / cr.loc["Interior", "customers_per_1000"] - 1)
fig, _ = figure("Interior regions: fewer buyers, same loyalty and spending",
                f"Coastal governorates have {gap:.0f}% more customers per inhabitant, "
                "but once people buy, they behave the same.",
                note="Coastal = Tunis, Ariana, Ben Arous, Manouba, Nabeul, Bizerte, Sousse, Monastir, Mahdia, "
                     "Sfax, Gabes, Medenine; Interior = the other 12. Population: INS census 2024.",
                plot_box=None)
for k, (lab, ser, fmt) in enumerate(panels):
    ax = fig.add_axes([0.08 + k * 0.30, 0.20, 0.24, 0.36])
    v = [ser["Coastal"], ser["Interior"]]
    ax.bar([0, 1], v, width=0.5, color=[COASTAL, INTERIOR])
    for xi, vi in zip([0, 1], v):
        ax.text(xi, vi * 1.02, fmt.format(vi), ha="center", va="bottom", fontsize=12, fontweight="bold")
    ax.set_xticks([0, 1], ["Coastal", "Interior"], fontsize=9)
    ax.tick_params(axis="x", length=0, colors=INK2)
    ax.set_ylim(0, max(v) * 1.25)
    ax.set_yticks([])
    ax.spines[["left", "top", "right"]].set_visible(False)
    ax.set_title(lab, fontsize=9.5, color=INK, loc="left", pad=12)
out.append(save(fig, "04_reach_not_spending"))

# ---------------------------------------------------------------- 5. governorate ranking
gv = read("02_geography_governorates").sort_values("orders_per_1000")
nat = (gv["orders"].sum() / gv["population_2024"].sum()) * 1000
fig, ax = figure("The North-East and the Sahel order the most per inhabitant",
                 "Orders per 1,000 inhabitants by governorate.",
                 note="Per 1,000 inhabitants over the whole data period (not per year). "
                      "Population: INS census 2024.",
                 plot_box=(0.25, 0.10, 0.68, 0.66))
yy = np.arange(len(gv))
ax.barh(yy, gv["orders_per_1000"], height=0.72,
        color=[COASTAL if r == "Coastal" else INTERIOR for r in gv["region"]])
ax.set_yticks(yy, gv["governorate"].str.replace("Medenine", "Médenine").str.replace("Gabes", "Gabès")
              .str.replace("Beja", "Béja").str.replace("Kebili", "Kébili").str.replace("Kef", "Le Kef"),
              fontsize=8)
ax.tick_params(axis="y", length=0)
ax.tick_params(axis="x", labelsize=7.5, colors=MUTED, length=0)
ax.set_xlim(0, 185)
ax.xaxis.grid(True)
ax.set_axisbelow(True)
ax.spines[["left", "bottom"]].set_visible(False)
ax.axvline(nat, color=INK, linewidth=0.9)
ax.set_ylim(-1.6, len(gv) - 0.4)
ax.text(nat + 2, -1.05, f"National average: {nat:.0f}", fontsize=7.5, color=INK, va="center")
for i in [0, len(gv) - 1]:
    v = gv["orders_per_1000"].iloc[i]
    ax.text(v + 2, i, f"{v:.0f}", va="center", fontsize=8, color=INK2)
for k, (lab, col) in enumerate([("Coastal", COASTAL), ("Interior", INTERIOR)]):
    fig.patches.append(__import__("matplotlib.patches", fromlist=["Rectangle"]).Rectangle(
        (0.08 + k * 0.17, 0.778), 0.018, 0.013, color=col, transform=fig.transFigure, figure=fig))
    fig.text(0.104 + k * 0.17, 0.784, lab, fontsize=8.5, color=INK2, va="center")
out.append(save(fig, "05_governorate_ranking"))

# ---------------------------------------------------------------- 6. Facebook vs reach
mix = read("03b_channel_mix_by_governorate").set_index("governorate")
geo = read("02_geography_governorates").set_index("governorate")
d = mix[["Facebook Page %", "region"]].join(geo["orders_per_1000"])
r = d["Facebook Page %"].corr(d["orders_per_1000"])
fig, ax = figure("Where fewer people buy, the Facebook Page matters more",
                 "Each dot is a governorate. TikTok Live leads everywhere, but Facebook's "
                 "share rises where reach is lower.",
                 note=f"Correlation across the 24 governorates: r = {r:.2f}. A pattern between regions, "
                      "not proof of cause.",
                 plot_box=(0.13, 0.13, 0.80, 0.56))
for reg, col in [("Coastal", COASTAL), ("Interior", INTERIOR)]:
    q = d[d["region"] == reg]
    ax.scatter(q["orders_per_1000"], q["Facebook Page %"], s=46, color=col, edgecolor=SURFACE,
               linewidth=1.2, label=reg, zorder=3)
m, c0 = np.polyfit(d["orders_per_1000"], d["Facebook Page %"], 1)
xs = np.array([65, 170])
ax.plot(xs, m * xs + c0, color=MUTED, linewidth=1, zorder=2)
for g, (dx, dy, ha) in {"Tataouine": (3, 0, "left"), "Tozeur": (3, 0.1, "left"), "Jendouba": (3, 0, "left"),
                        "Mahdia": (-3, 0.25, "right"), "Monastir": (3, -0.3, "left"),
                        "Ben Arous": (3, 0.3, "left"), "Tunis": (3, -0.35, "left")}.items():
    ax.text(d.loc[g, "orders_per_1000"] + dx, d.loc[g, "Facebook Page %"] + dy, g, fontsize=7.5,
            color=INK2, ha=ha, va="center")
ax.set_xlim(60, 185)
ax.set_xlabel("Orders per 1,000 inhabitants", fontsize=8.5)
ax.set_ylabel("Facebook Page share of orders (%)", fontsize=8.5)
ax.tick_params(labelsize=7.5, length=0)
ax.grid(True)
ax.set_axisbelow(True)
ax.spines[["left", "bottom"]].set_color(AXIS)
ax.legend(frameon=False, loc="upper right", fontsize=8.5, labelcolor=INK2, handletextpad=0.2)
out.append(save(fig, "06_facebook_vs_reach"))

# ---------------------------------------------------------------- 7. price bands
pb = read("05_price_bands_overall").set_index("band")
big = pb.loc[["120-200", "200+"]].sum()
fig, ax = figure("Big orders pay the bills",
                 f"Orders of 120 TND or more are {big['share_orders_pct']:.0f}% of orders "
                 f"but {big['share_revenue_pct']:.0f}% of revenue.",
                 note="Order value = product price, excluding delivery.",
                 plot_box=(0.10, 0.15, 0.84, 0.54))
x = np.arange(len(pb))
w = 0.38
ax.bar(x - w / 2 - 0.01, pb["share_orders_pct"], w, color=NEUTRAL, label="Share of orders")
ax.bar(x + w / 2 + 0.01, pb["share_revenue_pct"], w, color=ACCENT, label="Share of revenue")
for i in [4, 5]:
    ax.text(x[i] - w / 2, pb["share_orders_pct"].iloc[i] + 0.6, pct(pb["share_orders_pct"].iloc[i]),
            ha="center", fontsize=8.5, color=INK2)
    ax.text(x[i] + w / 2, pb["share_revenue_pct"].iloc[i] + 0.6, pct(pb["share_revenue_pct"].iloc[i]),
            ha="center", fontsize=8.5, color=INK, fontweight="bold")
ax.set_xticks(x, ["< 30", "30–50", "50–80", "80–120", "120–200", "200+"], fontsize=8.5)
ax.set_xlabel("Order value (TND)", fontsize=8.5)
ax.tick_params(axis="x", length=0, colors=INK2)
ax.tick_params(axis="y", labelsize=7.5, length=0)
ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")
ax.yaxis.grid(True)
ax.set_axisbelow(True)
ax.spines["left"].set_visible(False)
ax.legend(frameon=False, loc="lower left", bbox_to_anchor=(0, 1.02), ncol=2, fontsize=8.5, labelcolor=INK2)
out.append(save(fig, "07_price_bands"))

# ---------------------------------------------------------------- 8. estimated gender
ge = read("06_gender_estimated_overall").iloc[0]
f, m, u = (100 * ge[k] / ge["orders"] for k in ["F_orders", "M_orders", "unknown_orders"])
fig, ax = figure("Women's names are on at least 8 in 10 orders",
                 "Gender estimated from the customer's first name; ambiguous or unrecognized "
                 "names kept as unknown.",
                 note="Rough estimate: the name on an order may be the recipient's, not the buyer's.",
                 tag="Estimated", plot_box=(0.08, 0.40, 0.86, 0.14))
segs = [("Female name", f, ACCENT, "white"), ("Unknown", u, NEUTRAL, INK), ("Male name", m, INTERIOR, INK)]
left = 0
for lab, v, col, tc in segs:
    ax.barh(0, v, left=left, height=0.8, color=col, edgecolor=SURFACE, linewidth=2)
    if v > 10:
        ax.text(left + v / 2, 0, f"{lab}\n{v:.0f}%", ha="center", va="center", fontsize=10, color=tc,
                fontweight="bold" if lab.startswith("Female") else "normal")
    left += v
ax.annotate(f"Male name {m:.1f}%", xy=(100 - m / 2, -0.42), xytext=(100, -1.05), ha="right",
            fontsize=9, color=INK2, arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.8))
ax.set_xlim(0, 100)
ax.set_ylim(-1.3, 0.5)
ax.axis("off")
fig.text(0.08, 0.30, f"{ge['female_of_known_pct']:.0f}%", fontsize=34, fontweight="bold", color=ACCENT, va="top")
fig.text(0.33, 0.293, "of the names we could classify\nare women's names", fontsize=11, color=INK,
         va="top", linespacing=1.3)
fig.text(0.08, 0.205, f"Coverage: {ge['coverage_pct']:.0f}% of orders. Even if every unknown name were a man's,\n"
         f"women's names would still be {f:.0f}% of orders.", fontsize=8.5, color=INK2, va="top",
         linespacing=1.35)
out.append(save(fig, "08_gender_estimated"))

print("\n".join(str(p.relative_to(p.parents[2])) for p in out))
