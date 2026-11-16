"""Phase 1 - build the anonymized analysis file from the raw export.

Input : the raw CSV (read in place, never copied into the project)
Output: data/orders_anon.parquet with ONLY these columns
          customer_id  HMAC-SHA256(secret salt, client_gsm1), first 16 hex chars
          order_total  float, TND
          channel      TikTok Live / Facebook Page / Instagram / Website (Shopify) /
                       Reclamation / Unknown
          source_code  the cleaned raw channel code (keeps "0" vs "Instagram"
                       distinguishable inside Instagram)
          governorate  one of the 24 governorates, or Unknown
          gender_est   F / M / unknown - ESTIMATED from the first name

Steps: drop exact duplicate rows -> hash phone -> normalize channel and
governorate -> estimate gender -> drop every personal column -> shuffle rows.
Only aggregate counts are printed.

Why a salted HMAC and not a plain hash: Tunisian mobile numbers have 8 digits,
so a plain SHA-256 could be reversed by hashing all 10^8 numbers. The secret
salt (.secrets/salt.txt, never committed) makes that impossible.

Usage:
  python scripts/01_anonymize.py <raw.csv>
  python scripts/01_anonymize.py <raw.csv> --export-review   # private name review file
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import re
import secrets
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src import geo, names  # noqa: E402

SALT_PATH = ROOT / ".secrets" / "salt.txt"
OUT_PATH = ROOT / "data" / "orders_anon.parquet"
REVIEW_PATH = ROOT / "data" / "review" / "unmatched_first_names.csv"
REVIEW_MIN = 100  # only names shared by >= 100 orders go to the review file
OUT_COLS = ["customer_id", "order_total", "channel", "source_code", "governorate", "gender_est"]

CHANNEL_MAP = {  # cleaned raw code -> channel
    "Live": "TikTok Live",  # confirmed by the company: "Live" = TikTok Live
    "Page": "Facebook Page",
    "Instagram": "Instagram",
    "0": "Instagram",  # confirmed by the company: code 0 = Instagram page
    "Shopify": "Website (Shopify)",
    "Reclamation": "Reclamation",
    "missing": "Unknown",
}


def get_salt() -> bytes:
    if not SALT_PATH.exists():
        SALT_PATH.parent.mkdir(parents=True, exist_ok=True)
        SALT_PATH.write_text(secrets.token_hex(32))
    return SALT_PATH.read_text().strip().encode()


def clean_source(s: pd.Series) -> pd.Series:
    s = s.fillna("missing").astype(str).str.strip()
    s = s.where(~s.str.contains("clamation", case=False, regex=False), "Reclamation")
    return s.where(s.isin(CHANNEL_MAP), "other")


def pct(a: int, b: int) -> str:
    return f"{100 * a / b:6.2f}%"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("raw_csv")
    ap.add_argument("--export-review", action="store_true")
    args = ap.parse_args()

    try:
        raw = pd.read_csv(args.raw_csv, dtype=str, dtype_backend="pyarrow")
    except Exception as e:  # never echo messages that might quote raw lines
        sys.exit(f"Read failed: {type(e).__name__}")
    raw = raw.apply(lambda s: s.str.strip()).replace("", pd.NA)

    n_raw = len(raw)
    raw = raw.drop_duplicates().reset_index(drop=True)
    n = len(raw)
    dup_ids = int(raw["order_id"].duplicated().sum())
    print(f"Raw rows {n_raw:,} -> {n:,} after dropping {n_raw - n:,} exact duplicates "
          f"(order_ids still repeated with different content: {dup_ids:,})")
    if raw["client_gsm1"].isna().any():
        sys.exit("client_gsm1 has nulls - cannot build customer_id")

    # --- customer_id: keyed hash of the phone, computed once per distinct phone
    salt = get_salt()
    phones = raw["client_gsm1"].astype(str)
    ids = {p: hmac.new(salt, p.encode(), hashlib.sha256).hexdigest()[:16] for p in phones.unique()}
    customer_id = phones.map(ids)
    if customer_id.nunique() != len(ids):
        sys.exit("Hash collision detected - increase the id length")

    # --- channel
    source_code = clean_source(raw["order_source"])
    channel = source_code.map(CHANNEL_MAP).fillna("Unknown")

    # --- governorate: resolve each distinct label once, then rescue Unknowns from the address
    labels = raw["client_governorat"].astype(object)
    resolved = {lab: geo.resolve_label(lab) for lab in labels.dropna().unique()}
    gov = labels.map(lambda x: resolved.get(x, (geo.UNKNOWN, "unknown"))[0])
    gov_method = labels.map(lambda x: resolved.get(x, (geo.UNKNOWN, "unknown"))[1])
    unk = gov.eq(geo.UNKNOWN)
    from_addr = raw.loc[unk, "client_adresse"].map(geo.find_in_text)
    hit = from_addr.notna()
    gov.loc[from_addr[hit].index] = from_addr[hit]
    gov_method.loc[from_addr[hit].index] = "address"

    # --- estimated gender, once per distinct name
    lex = names.load_lexicon()
    nm = raw["client_nom"].astype(object)
    est = {x: names.estimate(x, lex) for x in nm.dropna().unique()}
    gender = nm.map(lambda x: est.get(x, ("unknown", "not_found"))[0])
    g_method = nm.map(lambda x: est.get(x, ("unknown", "not_found"))[1])

    if args.export_review:
        keys = nm[g_method.eq("not_found")].map(names.first_key)
        vc = keys[keys.str.len() > 1].value_counts()
        vc = vc[vc >= REVIEW_MIN]
        REVIEW_PATH.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame({"name": vc.index, "orders": vc.values, "gender": ""}).to_csv(REVIEW_PATH, index=False)
        print(f"\nPrivate review file written ({len(vc):,} first names, each on >= {REVIEW_MIN} orders, "
              f"covering {vc.sum():,} orders). It is gitignored and not displayed here.")

    out = pd.DataFrame({
        "customer_id": customer_id.astype(str),
        "order_total": pd.to_numeric(raw["order_total"]).astype("float64"),
        "channel": channel.astype("category"),
        "source_code": source_code.astype("category"),
        "governorate": gov.astype("category"),
        "gender_est": gender.astype("category"),
    })
    del raw, phones, nm, labels, ids, est, resolved

    # --- privacy assertions: refuse to write anything unexpected
    assert list(out.columns) == OUT_COLS, "unexpected columns"
    assert out["customer_id"].str.fullmatch(r"[0-9a-f]{16}").all(), "bad customer_id format"
    for c in ["channel", "source_code", "governorate", "gender_est"]:
        cats = [str(x) for x in out[c].cat.categories]
        assert not any(re.search(r"\d{8}", x) for x in cats), f"phone-like value in {c}"
    assert set(out["governorate"].cat.categories) <= set(geo.GOVERNORATES) | {geo.UNKNOWN}

    out = out.sample(frac=1, random_state=secrets.randbelow(2**32)).reset_index(drop=True)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    out.to_parquet(OUT_PATH, index=False)
    print(f"\nWrote {OUT_PATH.relative_to(ROOT)}  ({len(out):,} rows, columns {OUT_COLS})")

    print("\n== Governorate resolution (rows) ==")
    for m, c in gov_method.value_counts().items():
        print(f"  {m:10s} {c:>10,}  {pct(c, n)}")
    print(f"  -> final Unknown: {int(out['governorate'].eq(geo.UNKNOWN).sum()):,}")

    print("\n== Gender estimate method (rows) ==")
    for m, c in g_method.value_counts().items():
        print(f"  {m:10s} {c:>10,}  {pct(c, n)}")
    print(f"\n== Channel mapping (rows) ==")
    print(pd.crosstab(source_code, channel).to_string())


if __name__ == "__main__":
    main()
