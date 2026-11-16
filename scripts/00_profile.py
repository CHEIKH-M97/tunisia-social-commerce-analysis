"""Phase 0 - profile the raw orders file using aggregates only.

PRIVACY: this script never prints raw rows or any value from the personal
columns (client_nom, client_adresse, client_gsm1, client_gsm2). For those it
reports only null rates, distinct counts and format-check shares.
Category labels (order_source, client_governorat) are printed only when the
label covers at least MIN_GROUP rows, so no rare free-text value can leak.

Usage:  python scripts/00_profile.py <path-to-raw-csv>
"""
import sys

import pandas as pd

MIN_GROUP = 50
PII = ["client_nom", "client_adresse", "client_gsm1", "client_gsm2"]


def pct(x: float) -> str:
    return f"{100 * x:.2f}%"


def main(path: str) -> None:
    try:
        df = pd.read_csv(path, dtype=str, dtype_backend="pyarrow", keep_default_na=True)
    except Exception as e:  # never echo the message: parser errors can quote raw lines
        sys.exit(f"Read failed: {type(e).__name__}")

    n = len(df)
    print(f"Rows: {n:,}   Columns: {list(df.columns)}")
    print(f"Memory in pandas: {df.memory_usage(deep=True).sum() / 1e6:.0f} MB\n")

    # Blank strings count as missing too
    df = df.apply(lambda s: s.str.strip()).replace("", pd.NA)

    print("== Null rate and distinct count per column ==")
    for c in df.columns:
        print(f"  {c:20s} null={pct(df[c].isna().mean()):>8s}  distinct={df[c].nunique():>10,}")

    print("\n== order_id ==")
    print(f"  duplicated ids: {df['order_id'].duplicated().sum():,}")
    print(f"  fully duplicated rows: {df.duplicated().sum():,}")

    print("\n== order_total ==")
    tot = pd.to_numeric(df["order_total"].str.replace(",", ".", regex=False), errors="coerce")
    print(f"  non-numeric (after comma->dot): {tot.isna().sum() - df['order_total'].isna().sum():,}")
    q = tot.quantile([0, 0.01, 0.05, 0.25, 0.5, 0.75, 0.95, 0.99, 0.999, 1])
    for k, v in q.items():
        print(f"  p{k * 100:g}: {v:,.3f}")
    print(f"  mean: {tot.mean():,.3f}   sum: {tot.sum():,.0f}")
    print(f"  <= 0: {(tot <= 0).sum():,}   > 1000: {(tot > 1000).sum():,}   > 5000: {(tot > 5000).sum():,}")

    for col in ["order_source", "client_governorat"]:
        vc = df[col].value_counts(dropna=False)
        big, small = vc[vc >= MIN_GROUP], vc[vc < MIN_GROUP]
        print(f"\n== {col}: {len(vc)} distinct labels; {len(big)} with >= {MIN_GROUP} rows ==")
        for label, cnt in big.items():
            print(f"  {str(label)!s:30.30s} {cnt:>10,}  {pct(cnt / n):>8s}")
        print(f"  ...{len(small)} other labels covering {small.sum():,} rows (not shown)")

    print("\n== Phone format checks (shares only) ==")
    for col in ["client_gsm1", "client_gsm2"]:
        s = df[col].dropna()
        digits = s.str.replace(r"\D", "", regex=True)
        print(f"  {col}: non-null={len(s):,}")
        print(f"    exactly 8 digits as stored : {pct(s.str.fullmatch(r'\d{8}').mean())}")
        print(f"    8 digits after stripping non-digits: {pct(digits.str.len().eq(8).mean())}")
        print(f"    starts with 216 / +216 / 00216 (11+ digits): {pct((digits.str.len() >= 11).mean())}")
        print(f"    other lengths: {pct((~digits.str.len().isin([8, 11, 13])).mean())}")
    both = df[["client_gsm1", "client_gsm2"]].dropna()
    print(f"  rows where gsm2 == gsm1: {(both['client_gsm1'] == both['client_gsm2']).sum():,}")

    print("\n== Customers (via client_gsm1) ==")
    per = df["client_gsm1"].value_counts()
    print(f"  distinct gsm1: {len(per):,}")
    print(f"  customers with >1 order: {pct((per > 1).mean())}")
    print(f"  orders per customer: median={per.median():.0f}  p99={per.quantile(0.99):.0f}  max={per.max():,}")
    print(f"  customers with >= 50 orders: {(per >= 50).sum():,} (covering {per[per >= 50].sum():,} orders)")

    print("\n== client_nom shape (for optional gender step) ==")
    nom = df["client_nom"].dropna()
    tokens = nom.str.split().str.len()
    print(f"  tokens per name: 1={pct(tokens.eq(1).mean())}  2={pct(tokens.eq(2).mean())}  3+={pct(tokens.ge(3).mean())}")
    print(f"  contains Arabic script: {pct(nom.str.contains(r'[؀-ۿ]', regex=True).mean())}")
    print(f"  contains digits: {pct(nom.str.contains(r'\d', regex=True).mean())}")

    print("\n== client_adresse ==")
    print(f"  median length (chars): {df['client_adresse'].str.len().median():.0f}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
