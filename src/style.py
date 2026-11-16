"""One visual style for every chart and the carousel.

Palette: validated reference palette (dataviz skill) - slot 1 blue as the single
accent, slot 2 orange only when two groups must be told apart (coastal vs
interior), neutral grey for context. Checked with validate_palette.js
(light, all-pairs): all checks pass.
Format: 1080 x 1350 px (LinkedIn portrait), system sans (Segoe UI).
"""
from __future__ import annotations

import textwrap
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
CHARTS = ROOT / "outputs" / "charts"

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"
ACCENT = "#2a78d6"   # slot 1 - the story
ORANGE = "#eb6834"   # slot 2 - second group only
NEUTRAL = "#b5b4ad"  # context bars
COASTAL, INTERIOR = ACCENT, ORANGE

FIGSIZE, DPI = (5.4, 6.75), 200  # -> 1080 x 1350 px
SOURCE = "Source: 1,494,712 anonymized sales orders from one Tunisian e-commerce company."

plt.rcParams.update({
    "font.family": "Segoe UI",
    "font.size": 9,
    "text.color": INK,
    "axes.edgecolor": AXIS,
    "axes.labelcolor": INK2,
    "axes.facecolor": SURFACE,
    "figure.facecolor": SURFACE,
    "xtick.color": MUTED,
    "ytick.color": INK2,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": False,
    "grid.color": GRID,
    "grid.linewidth": 0.6,
})


def figure(title: str, subtitle: str, note: str = "", tag: str = "",
           plot_box=(0.08, 0.13, 0.86, 0.60)):
    """Create a figure with the standard header/footer and one plot area."""
    fig = plt.figure(figsize=FIGSIZE, dpi=DPI)
    y = 0.955
    if tag:  # small uppercase kicker, e.g. ESTIMATED
        fig.text(0.08, y, tag.upper(), fontsize=8, fontweight="bold", color=ORANGE, va="top")
        y -= 0.03
    t = "\n".join(textwrap.wrap(title, 30))
    fig.text(0.08, y, t, fontsize=17, fontweight="bold", color=INK, va="top", linespacing=1.15)
    y -= 0.047 * (t.count("\n") + 1) + 0.018
    fig.text(0.08, y, "\n".join(textwrap.wrap(subtitle, 62)), fontsize=9.5, color=INK2, va="top",
             linespacing=1.3)
    foot = "\n".join(textwrap.wrap(f"{note} {SOURCE}".strip(), 92))
    fig.text(0.08, 0.025, foot, fontsize=6.6, color=MUTED, va="bottom", linespacing=1.35)
    ax = fig.add_axes(plot_box) if plot_box else None
    return fig, ax


def clean_hbar(ax):
    """Horizontal bars with direct labels: no x axis, no box."""
    ax.spines[["top", "right", "bottom"]].set_visible(False)
    ax.spines["left"].set_color(AXIS)
    ax.tick_params(axis="x", bottom=False, labelbottom=False)
    ax.tick_params(axis="y", length=0, labelsize=10, pad=6)


def save(fig, name: str) -> Path:
    CHARTS.mkdir(parents=True, exist_ok=True)
    path = CHARTS / f"{name}.png"
    fig.savefig(path, dpi=DPI, facecolor=SURFACE)
    plt.close(fig)
    return path
