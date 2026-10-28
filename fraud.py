"""Real-time fraud detection on top of the Customer 360.

Transactions arrive per source-system account; the golden-record crosswalk links every account
to one customer, so behavioral features use the customer's full history across systems.
Scoring = interpretable rules + a dependency-free logistic regression (numpy).
"""
import numpy as np
import pandas as pd

HOME_COUNTRY = "AA"
FEATURES = ["amount_z", "log_amount", "amount_vs_max", "txn_count_1h", "new_device", "foreign",
            "fast_city_change", "night", "online"]


def build_features(txns, xref, home_country=HOME_COUNTRY):
    t = txns.merge(xref[["record_key", "customer_id"]], left_on="account_ref", right_on="record_key", how="left")
    t = t.drop(columns="record_key")
    t["ts"] = pd.to_datetime(t["ts"])
    t = t.sort_values(["customer_id", "ts"]).reset_index(drop=True)
    g = t.groupby("customer_id", sort=False)
    prior_mean = g["amount"].transform(lambda s: s.shift().expanding().mean())
    prior_std = g["amount"].transform(lambda s: s.shift().expanding().std())
    prior_max = g["amount"].transform(lambda s: s.shift().expanding().max())
    t["amount_z"] = ((t.amount - prior_mean) / prior_std.replace(0, np.nan)).fillna(0).clip(-5, 20)
    t["amount_vs_max"] = (t.amount / prior_max).fillna(1).clip(0, 50)
    t["log_amount"] = np.log1p(t.amount)
    secs = (t.ts.astype("int64") // 10**9).values
    cnt = np.zeros(len(t), dtype=int)
    for _, idx in g.indices.items():
        s = secs[idx]
        cnt[idx] = np.arange(len(idx)) - np.searchsorted(s, s - 3600, side="left")
    t["txn_count_1h"] = cnt                                   # prior txns in the last hour
    first_seen = t.groupby(["customer_id", "device_id"]).cumcount() == 0
    t["new_device"] = (first_seen & (g.cumcount() > 0)).astype(int)
    t["foreign"] = (t.merchant_country != home_country).astype(int)
    prev_city, prev_ts = g.city.shift(), g.ts.shift()
    t["fast_city_change"] = ((t.city != prev_city) & prev_city.notna() &
                             ((t.ts - prev_ts).dt.total_seconds() < 7200)).astype(int)
    t["night"] = t.ts.dt.hour.between(0, 5).astype(int)
    t["online"] = (t.channel == "card_online").astype(int)
    return t


def rule_score(f):
    """Interpretable rules an analyst can read; also a fallback if the model is unavailable."""
    s = (0.30 * (f.txn_count_1h >= 3) + 0.25 * f.new_device + 0.20 * f.foreign +
         0.20 * f.fast_city_change + 0.15 * (f.amount_z > 4) + 0.10 * f.night)
    return s.clip(0, 1)


class LogisticModel:
    """Class-weighted L2 logistic regression with gradient descent; no ML library required."""

    def __init__(self, lr=0.5, epochs=3000, l2=1e-3):
        self.lr, self.epochs, self.l2 = lr, epochs, l2

    def fit(self, X, y):
        X, y = np.asarray(X, float), np.asarray(y, float)
        self.mu, self.sd = X.mean(0), X.std(0) + 1e-9
        Xb = np.c_[np.ones(len(X)), (X - self.mu) / self.sd]
        pos = max(y.mean(), 1e-6)
        sw = np.where(y == 1, 0.5 / pos, 0.5 / (1 - pos))
        w = np.zeros(Xb.shape[1])
        for _ in range(self.epochs):
            p = 1 / (1 + np.exp(-Xb @ w))
            grad = Xb.T @ ((p - y) * sw) / len(y) + self.l2 * np.r_[0, w[1:]]
            w -= self.lr * grad
        self.w = w
        return self

    def predict_proba(self, X):
        X = np.asarray(X, float)
        return 1 / (1 + np.exp(-(np.c_[np.ones(len(X)), (X - self.mu) / self.sd] @ self.w)))

    def weights(self, names=FEATURES):
        return pd.Series(self.w[1:], index=names).sort_values(ascending=False)


def auc(y, p):
    y, p = np.asarray(y), np.asarray(p)
    order = p.argsort()
    ranks = np.empty(len(p))
    ranks[order] = np.arange(1, len(p) + 1)
    npos, nneg = y.sum(), len(y) - y.sum()
    return float((ranks[y == 1].sum() - npos * (npos + 1) / 2) / (npos * nneg)) if npos and nneg else float("nan")


def decide(score, block=0.95, step_up=0.85):
    return np.where(score >= block, "BLOCK", np.where(score >= step_up, "STEP_UP", "APPROVE"))


def train_and_score(features, train_frac=0.7, model_weight=0.7):
    """Time-based split (train on earlier days, test on later) -> scores, decisions and metrics."""
    f = features.sort_values("ts").reset_index(drop=True)
    cut = f.ts.min() + (f.ts.max() - f.ts.min()) * train_frac
    train, test = f[f.ts < cut], f[f.ts >= cut].copy()
    model = LogisticModel().fit(train[FEATURES], train.is_fraud)
    test["model_score"] = model.predict_proba(test[FEATURES])
    test["rule_score"] = rule_score(test)
    test["fraud_score"] = model_weight * test.model_score + (1 - model_weight) * test.rule_score
    test["decision"] = decide(test.fraud_score.values)
    k = int(test.is_fraud.sum())
    top = test.nlargest(max(k, 1), "fraud_score")
    flagged = test[test.decision != "APPROVE"]
    metrics = dict(train_txns=len(train), test_txns=len(test), test_fraud=k,
                   auc_model=round(auc(test.is_fraud, test.model_score), 3),
                   auc_rules=round(auc(test.is_fraud, test.rule_score), 3),
                   auc_combined=round(auc(test.is_fraud, test.fraud_score), 3),
                   precision_at_k=round(float(top.is_fraud.mean()), 3),
                   flagged=len(flagged),
                   recall_flagged=round(float(flagged.is_fraud.sum() / k), 3) if k else None,
                   precision_flagged=round(float(flagged.is_fraud.mean()), 3) if len(flagged) else None)
    return model, test, metrics


def score_one(model, feature_row, model_weight=0.7):
    """Score a single, already-featurized transaction (what a streaming consumer would call)."""
    fr = pd.DataFrame([feature_row])
    s = model_weight * model.predict_proba(fr[FEATURES])[0] + (1 - model_weight) * float(rule_score(fr).iloc[0])
    return dict(fraud_score=round(float(s), 3), decision=str(decide(np.array([s]))[0]))
