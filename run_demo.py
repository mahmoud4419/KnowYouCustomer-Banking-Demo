"""End-to-end local run (no AWS needed):  python scripts/run_demo.py [--publish --database db --s3 s3://... --workgroup wg]"""
import argparse, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from lumora import c360, fraud, aws_io

ap = argparse.ArgumentParser()
ap.add_argument("--data", default=os.path.join(os.path.dirname(__file__), "..", "data", "sample"))
ap.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "..", "output"))
ap.add_argument("--publish", action="store_true")
ap.add_argument("--database"); ap.add_argument("--s3"); ap.add_argument("--workgroup")
a = ap.parse_args()
rd = lambda n: aws_io.read_csv(f"{a.data}/{n}.csv")
t24, crm, cards = rd("core_banking_customers"), rd("crm_contacts"), rd("cards_accounts")
res = c360.run(t24, crm, cards)
print("Customer 360:", c360.evaluate(res["silver"], rd("ground_truth").astype({"person_id": int})), res["links"])
txns = rd("transactions").astype({"amount": float, "is_fraud": int})
feats = fraud.build_features(txns, res["xref"])
model, scored, metrics = fraud.train_and_score(feats)
print("Fraud:", metrics)
os.makedirs(a.out, exist_ok=True)
for name, df in [("gold_customer_360", res["gold"]), ("gold_customer_xref", res["xref"]), ("fraud_scored_txns", scored)]:
    df.to_csv(f"{a.out}/{name}.csv", index=False)
if a.publish:
    aws_io.publish({"silver_customer_records": res["silver"], "gold_customer_360": res["gold"],
                    "gold_customer_xref": res["xref"], "fraud_scored_txns": scored}, a.database, a.s3, a.workgroup)
