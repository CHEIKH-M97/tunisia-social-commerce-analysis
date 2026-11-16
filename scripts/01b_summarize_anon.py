"""Phase 1 check - summary stats and privacy checks on the anonymized file only."""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "data" / "orders_anon.parquet"
EXPECTED = ["customer_id", "order_total", "channel", "source_code", "governorate", "gender_est"]

df = pd.read_parquet(PATH)
n = len(df)
print(f"File: {PATH.relative_to(ROOT)}  {PATH.stat().st_size / 1e6:.1f} MB  rows={n:,}")

print("\n== Privacy checks ==")
print(f"  columns exactly as expected: {list(df.columns) == EXPECTED}")
print(f"  customer_id all 16-hex: {df['customer_id'].str.fullmatch(r'[0-9a-f]{16}').all()}")
# customer_id is excluded: random hex legitimately contains 8-digit runs ~9.3% of the time
print(f"  any 8-digit value in category columns: "
      f"{any(df[c].astype(str).str.contains(r'\d{8}').any() for c in EXPECTED[2:])}")

print("\n== Nulls ==")
print("  " + ", ".join(f"{c}={df[c].isna().sum()}" for c in df.columns))

print("\n== Customers ==")
per = df.groupby("customer_id").size()
print(f"  distinct customers: {len(per):,}   orders/customer: mean {per.mean():.2f}, median {per.median():.0f}, max {per.max()}")

print("\n== order_total (TND) ==")
t = df["order_total"]
print("  " + "  ".join(f"p{int(q * 100)}={t.quantile(q):.1f}" for q in [0.01, 0.25, 0.5, 0.75, 0.99]))
print(f"  sum={t.sum():,.0f}   zero={int((t == 0).sum()):,}   negative={int((t < 0).sum()):,}")

print("\n== Channel ==")
ch = df.groupby("channel", observed=True)["order_total"].agg(orders="size", revenue="sum", median="median")
ch["share_orders"] = (100 * ch["orders"] / n).round(2)
print(ch.sort_values("orders", ascending=False).round(1).to_string())

print("\n== Governorate (orders) ==")
g = df["governorate"].value_counts()
print(f"  {len(g)} values ({(g.index != 'Unknown').sum()} governorates + Unknown)")
print("  " + "\n  ".join(f"{k:12s} {v:>8,}" for k, v in g.items()))

print("\n== gender_est (ESTIMATED) ==")
ge = df["gender_est"].value_counts()
print("  per order: " + ", ".join(f"{k}={v:,} ({100 * v / n:.1f}%)" for k, v in ge.items()))
known = ge.drop("unknown", errors="ignore")
print("  among known: " + ", ".join(f"{k}={100 * v / known.sum():.1f}%" for k, v in known.items()))
# customer-level: a customer's orders can carry different names -> check consistency
gc = df[df["gender_est"] != "unknown"].groupby("customer_id")["gender_est"].nunique()
print(f"  customers with a known estimate: {len(gc):,}; of these, conflicting F/M across orders: "
      f"{int((gc > 1).sum()):,} ({100 * (gc > 1).mean():.1f}%)")
