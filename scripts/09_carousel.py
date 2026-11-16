"""Phase 3 - 8-slide LinkedIn carousel (PDF, 1080 x 1350 per page).

Slide 1 cover, slides 2-7 the approved charts, slide 8 takeaways + method + limits.
Every number on the cover and closing slide is read from outputs/tables.
"""
import sys
import textwrap
from pathlib import Path

import matplotlib.image as mpimg
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.style import ACCENT, DPI, FIGSIZE, INK, INK2, MUTED, ORANGE, SURFACE, plt  # noqa: E402
from matplotlib.backends.backend_pdf import PdfPages  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
T, CH = ROOT / "outputs" / "tables", ROOT / "outputs" / "charts"
OUT = ROOT / "outputs" / "carousel"
(OUT / "slides").mkdir(parents=True, exist_ok=True)
plt.rcParams["pdf.fonttype"] = 42  # embed TrueType fonts
read = lambda n: pd.read_csv(T / f"{n}.csv")  # noqa: E731

ch = read("01_channel_performance").set_index("channel")
bk = read("04_orders_per_customer").set_index("bucket")
cr = read("02b_coastal_vs_interior").set_index("region")
sc = read("04e_repeat_single_channel_customers").set_index("customer_group")
pb = read("05_price_bands_overall").set_index("band")
conc = read("04b_revenue_concentration").set_index("top_customers_pct")
gv = read("02_geography_governorates")

N_SALES = int(ch.loc["All sales", "orders"])
TIKTOK = ch.loc["TikTok Live", "share_orders_pct"]
REPEAT_REV = 100 - bk.loc["1 order", "share_revenue_pct"]
REPEAT_CUST = 100 - bk.loc["1 order", "share_customers_pct"]
COAST_GAP = 100 * (cr.loc["Coastal", "customers_per_1000"] / cr.loc["Interior", "customers_per_1000"] - 1)
TT_REP, FB_REP = sc.loc["TikTok Live", "repeat_rate_pct"], sc.loc["Facebook Page", "repeat_rate_pct"]
BIG = pb.loc[["120-200", "200+"]].sum()
TOP10 = conc.loc[10, "share_revenue_pct"]
CHARTS = ["01_channel_mix", "03_tiktok_loyalty", "02_repeat_customers", "04_reach_not_spending",
          "06_facebook_vs_reach", "07_price_bands"]
TOTAL = 2 + len(CHARTS)


def page_no(fig, i):
    fig.text(0.92, 0.968, f"{i}/{TOTAL}", fontsize=8, color=MUTED, ha="right", va="top")


def cover():
    fig = plt.figure(figsize=FIGSIZE, dpi=DPI)
    fig.text(0.08, 0.90, "DATA PROJECT  ·  TUNISIA", fontsize=8.5, fontweight="bold", color=ORANGE)
    fig.text(0.08, 0.865, "How Tunisians buy\non social media", fontsize=27, fontweight="bold", color=INK,
             va="top", linespacing=1.1)
    fig.text(0.08, 0.715, "\n".join(textwrap.wrap(
        f"What {N_SALES / 1e6:.1f} million orders from a Tunisian e-commerce company reveal, "
        "for small sellers and startups.", 46)), fontsize=11.5, color=INK2, va="top", linespacing=1.35)
    stats = [(f"{TIKTOK:.0f}%", "of orders come from TikTok Live"),
             (f"{REPEAT_REV:.0f}%", "of revenue comes from repeat customers"),
             (f"+{COAST_GAP:.0f}%", "more buyers per inhabitant on the coast,\nbut the interior spends the same")]
    y = 0.56
    for big, lab in stats:
        fig.add_artist(plt.Line2D([0.08, 0.92], [y + 0.012, y + 0.012], color="#e1e0d9", lw=0.8))
        fig.text(0.08, y - 0.008, big, fontsize=30, fontweight="bold", color=ACCENT, va="top")
        fig.text(0.42, y - 0.022, lab, fontsize=10.5, color=INK, va="top", linespacing=1.3)
        y -= 0.135
    fig.text(0.08, 0.07, "Anonymized and aggregated data. Company not named.", fontsize=7.5, color=MUTED)
    fig.text(0.92, 0.07, "Swipe  →", fontsize=11, color=ACCENT, fontweight="bold", ha="right")
    page_no(fig, 1)
    return fig


def chart_slide(name, i):
    fig = plt.figure(figsize=FIGSIZE, dpi=DPI)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.imshow(mpimg.imread(CH / f"{name}.png"))
    ax.axis("off")
    page_no(fig, i)
    return fig


def closing():
    fig = plt.figure(figsize=FIGSIZE, dpi=DPI)
    fig.text(0.08, 0.93, "What a small seller can take from this", fontsize=17, fontweight="bold",
             color=INK, va="top")
    tips = [f"Go live on TikTok. It brings {TIKTOK:.0f}% of orders, and its buyers come back "
            f"{TT_REP / FB_REP:.1f}x as often.",
            f"Win the second sale. Repeat buyers ({REPEAT_CUST:.0f}% of customers) bring {REPEAT_REV:.0f}% "
            f"of revenue; the top 10% alone bring {TOP10:.0f}%.",
            "Don't write off the interior: fewer buyers, but the same spending and loyalty.",
            "Outside the big coastal cities, keep your Facebook Page active.",
            f"Offer bundles or premium items: orders of 120 TND+ are {BIG['share_orders_pct']:.0f}% of orders "
            f"but {BIG['share_revenue_pct']:.0f}% of revenue."]
    y = 0.86
    for k, t in enumerate(tips, 1):
        fig.text(0.08, y, f"{k}", fontsize=13, fontweight="bold", color=ACCENT, va="top")
        w = "\n".join(textwrap.wrap(t, 52))
        fig.text(0.14, y, w, fontsize=9.8, color=INK, va="top", linespacing=1.3)
        y -= 0.027 * (w.count("\n") + 1) + 0.03
    blocks = [("How it was done",
               f"{N_SALES:,} sales orders from one Tunisian e-commerce company, shared with permission. "
               "Exact duplicates removed. Customers identified only by a salted hash of their phone number; "
               "names, phones and addresses never left the source file. No group under 50 orders is shown. "
               "Population: INS census 2024. Python + pandas."),
              ("Limits",
               "One company: its channel mix reflects its own strategy, not the whole market. No dates: "
               "rates cover the full period, not a year. Patterns, not proven causes. "
               "Gender (in the full report) is estimated from first names.")]
    y -= 0.03
    for head, body in blocks:
        fig.add_artist(plt.Line2D([0.08, 0.92], [y + 0.012, y + 0.012], color="#e1e0d9", lw=0.8))
        fig.text(0.08, y, head.upper(), fontsize=8, fontweight="bold", color=ORANGE, va="top")
        w = "\n".join(textwrap.wrap(body, 74))
        fig.text(0.08, y - 0.03, w, fontsize=8.3, color=INK2, va="top", linespacing=1.35)
        y -= 0.03 + 0.023 * (w.count("\n") + 1) + 0.035
    fig.text(0.08, 0.05, "Full code, tables and method on GitHub (link in the post).", fontsize=8.5,
             color=ACCENT, fontweight="bold")
    page_no(fig, TOTAL)
    return fig


slides = [cover()] + [chart_slide(n, i) for i, n in enumerate(CHARTS, 2)] + [closing()]
pdf_path = OUT / "tunisia_social_commerce_carousel.pdf"
with PdfPages(pdf_path) as pdf:
    for i, fig in enumerate(slides, 1):
        fig.savefig(OUT / "slides" / f"slide_{i:02d}.png", dpi=DPI, facecolor=SURFACE)
        pdf.savefig(fig, facecolor=SURFACE)
        plt.close(fig)
print(f"{pdf_path.relative_to(ROOT)}  ({pdf_path.stat().st_size / 1e6:.1f} MB, {len(slides)} pages)")
