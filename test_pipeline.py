import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from lumora import datagen, c360, fraud


def test_customer360_resolves_exactly():
    t24, crm, cards, truth, persons = datagen.generate_customers(200, seed=42)
    res = c360.run(t24, crm, cards)
    ev = c360.evaluate(res["silver"], truth)
    assert ev["false_merges"] == 0 and ev["missed_matches"] == 0
    assert ev["golden_customers"] == ev["true_customers"]


def test_fraud_model_separates():
    t24, crm, cards, truth, persons = datagen.generate_customers(200, seed=42)
    res = c360.run(t24, crm, cards)
    feats = fraud.build_features(datagen.generate_transactions(persons), res["xref"])
    _, _, m = fraud.train_and_score(feats)
    assert m["auc_combined"] > 0.9
