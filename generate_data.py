"""Regenerate the synthetic sample data:  python scripts/generate_data.py --customers 200"""
import argparse, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from lumora import datagen

ap = argparse.ArgumentParser()
ap.add_argument("--customers", type=int, default=200)
ap.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "..", "data", "sample"))
ap.add_argument("--seed", type=int, default=42)
a = ap.parse_args()
os.makedirs(a.out, exist_ok=True)
t24, crm, cards, truth, persons = datagen.generate_customers(a.customers, seed=a.seed)
txns = datagen.generate_transactions(persons)
for name, df in [("core_banking_customers", t24), ("crm_contacts", crm), ("cards_accounts", cards),
                 ("ground_truth", truth), ("transactions", txns)]:
    df.to_csv(os.path.join(a.out, f"{name}.csv"), index=False, encoding="utf-8")
    print(f"{name}: {len(df)} rows")
