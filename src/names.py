"""Rough gender estimate from a customer's name. ESTIMATE ONLY.

Rules, in order:
  1. title   - a leading title (Mme, Mlle, Madame / Mr, Monsieur, Si) decides
  2. first   - first word found in the dictionary as M or F
  ambiguous  - the first word is a unisex name (e.g. Nour)
  not_found  - nothing matched
El/Al before a first name is skipped. Anything not M/F is "unknown".

The dictionary is reference/first_names_gender.csv (written from general
knowledge, not from the data). Optional private manual labels are read from
data/review/manual_labels.csv (columns: name, gender) and take precedence.
"""
from __future__ import annotations

import re
import unicodedata
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DICT_PATH = ROOT / "reference" / "first_names_gender.csv"
MANUAL_PATH = ROOT / "data" / "review" / "manual_labels.csv"

TITLE_F = {"mme", "madame", "mlle", "mademoiselle", "mrs", "miss", "lella"}
TITLE_M = {"mr", "monsieur", "mister", "si", "sidi"}
PARTICLES_SKIP = {"el", "al"}


def _ascii_words(text: object) -> list[str]:
    if not isinstance(text, str):
        return []
    t = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z]+", " ", t).split()


def _collapse(word: str) -> str:
    return re.sub(r"(.)\1+", r"\1", word)  # mohammed -> mohamed, sarra -> sara


def load_lexicon() -> dict[str, str]:
    frames = [pd.read_csv(DICT_PATH)]
    if MANUAL_PATH.exists():
        frames.append(pd.read_csv(MANUAL_PATH))  # later rows win
    lex: dict[str, str] = {}
    for df in frames:
        for name, g in zip(df["name"], df["gender"].str.upper().str.strip()):
            if g not in {"M", "F", "U"}:
                continue
            key = _collapse(str(name).strip().lower())
            prev = lex.get(key)
            # a key that collapses to both M and F in the base dictionary becomes unisex
            lex[key] = "U" if (prev and prev != g and df is frames[0]) else g
    return lex


def estimate(name: object, lex: dict[str, str]) -> tuple[str, str]:
    """Return (gender_est in {F, M, unknown}, method)."""
    words = _ascii_words(name)
    if not words:
        return "unknown", "not_found"
    if words[0] in TITLE_F:
        return "F", "title"
    if words[0] in TITLE_M:
        return "M", "title"
    words = [_collapse(w) for w in words]
    if words[0] in PARTICLES_SKIP and len(words) > 1:
        words = words[1:]

    g = lex.get(words[0])
    if g in {"M", "F"}:
        return g, "first"
    if g == "U":
        return "unknown", "ambiguous"
    # No fallback to the second word: Tunisian names are often written
    # "Firstname Fathersname", so the second word is frequently the father's
    # (male) name. Testing showed that fallback marked 11% of its orders male
    # vs 4% for first-word matches, i.e. a male bias. Dropped on purpose.
    return "unknown", "not_found"


def first_key(name: object) -> str:
    """Normalized first word after titles/particles - used only for the private review file."""
    words = [w for w in _ascii_words(name) if w not in TITLE_F | TITLE_M]
    words = [_collapse(w) for w in words]
    if words and words[0] in PARTICLES_SKIP and len(words) > 1:
        words = words[1:]
    return words[0] if words else ""
