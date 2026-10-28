"""Customer 360 / MDM: standardize -> identity resolution -> survivorship -> golden record."""
import re
import difflib
import pandas as pd

TRANSLIT = [("oo", "u"), ("ou", "u"), ("ee", "i"), ("ie", "i"), ("ah", "a"), ("kh", "k"), ("dh", "d"),
            ("sh", "s"), ("ph", "f"), ("y", "i"), ("e", "a"), ("o", "u")]
SOURCE_PRIORITY = {"T24": 1, "CRM": 2, "CARDS": 3}   # core banking is the system of record


def _s(x):
    return "" if x is None or (isinstance(x, float) and pd.isna(x)) else str(x)


def std_phone(x, country_code="990"):
    d = re.sub(r"\D", "", _s(x))
    d = re.sub(rf"^(00{country_code}|{country_code}|0)", "", d)
    return d if len(d) == 9 else None


def std_national_id(x):
    d = re.sub(r"\D", "", _s(x))
    return d if len(d) == 15 else None


def std_date(x):
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y%m%d"):
        try:
            d = pd.to_datetime(_s(x), format=fmt)
            if pd.notna(d):
                return d.date().isoformat()
        except (ValueError, TypeError):
            pass
    return None


def name_key(x):
    """Transliteration-tolerant name key (Mohammed/Mohamed, Al Mansoori/Almansouri)."""
    x = _s(x).lower().replace("-", " ").replace("'", "")
    x = re.sub(r"\bal\s+", "al", x)
    x = re.sub(r"\s+", " ", x).strip()
    for a, b in TRANSLIT:
        x = x.replace(a, b)
    return re.sub(r"(.)\1", r"\1", x)


def standardize(t24, crm, cards, country_code="990"):
    """Union three source extracts into one canonical 'silver' schema."""
    num = lambda s: pd.to_numeric(s, errors="coerce")
    a = pd.DataFrame(dict(source="T24", source_id=t24.cif_id, name_en=t24.full_name, name_ar=None, mobile=t24.mobile,
                          national_id=t24.national_id, dob_raw=t24.date_of_birth, email=None, city=t24.city,
                          segment=t24.segment, casa_balance=num(t24.casa_balance), card_product=None, credit_limit=None,
                          card_outstanding=None, preferred_language=None, record_date=t24.last_updated))
    b = pd.DataFrame(dict(source="CRM", source_id=crm.contact_id, name_en=crm.name_en, name_ar=crm.name_ar,
                          mobile=crm.mobile, national_id=crm.national_id, dob_raw=crm.date_of_birth,
                          email=crm.email.map(lambda e: _s(e).lower() or None), city=None, segment=None,
                          casa_balance=None, card_product=None, credit_limit=None, card_outstanding=None,
                          preferred_language=crm.preferred_language, record_date=crm.last_contact_date))
    c = pd.DataFrame(dict(source="CARDS", source_id=cards.card_account_id, name_en=cards.cardholder_name, name_ar=None,
                          mobile=cards.mobile, national_id=None, dob_raw=cards.date_of_birth,
                          email=cards.email.map(lambda e: _s(e).lower() or None), city=None, segment=None,
                          casa_balance=None, card_product=cards.card_product, credit_limit=num(cards.credit_limit),
                          card_outstanding=num(cards.outstanding), preferred_language=None, record_date=None))
    s = pd.concat([a, b, c], ignore_index=True)
    for col in ["casa_balance", "credit_limit", "card_outstanding"]:
        s[col] = pd.to_numeric(s[col], errors="coerce")
    s["mobile_std"] = s.mobile.map(lambda v: std_phone(v, country_code))
    s["national_id_std"] = s.national_id.map(std_national_id)
    s["dob"] = s.dob_raw.map(std_date)
    s["name_key"] = s.name_en.map(name_key)
    s["record_key"] = s.source + ":" + s.source_id.astype(str)
    return s


def resolve(silver, fuzzy_threshold=0.85):
    """Deterministic (national ID, mobile, email) + fuzzy (name similarity within same DOB) matching,
    clustered with union-find. Returns (silver_with_customer_id, links_per_rule)."""
    s = silver.copy()
    parent = {k: k for k in s.record_key}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        parent[find(a)] = find(b)

    links = {}
    for col, rule in [("national_id_std", "national_id"), ("mobile_std", "mobile"), ("email", "email")]:
        n = 0
        for _, g in s[s[col].notna()].groupby(col):
            keys = list(g.record_key)
            for k in keys[1:]:
                union(keys[0], k)
                n += 1
        links[rule] = n
    n = 0
    for _, g in s[s.dob.notna() & (s.name_key != "")].groupby("dob"):   # blocking on DOB
        rows = g[["record_key", "name_key"]].values.tolist()
        for i in range(len(rows)):
            for j in range(i + 1, len(rows)):
                if difflib.SequenceMatcher(None, rows[i][1], rows[j][1]).ratio() >= fuzzy_threshold:
                    union(rows[i][0], rows[j][0])
                    n += 1
    links["fuzzy_name_dob"] = n
    s["cluster"] = s.record_key.map(find)
    ids = {c: f"CUS-{i:05d}" for i, c in enumerate(sorted(s.cluster.unique()), 1)}
    s["customer_id"] = s.cluster.map(ids)
    return s.drop(columns="cluster"), links


def build_golden(resolved):
    """Survivorship rules -> one golden record per customer, plus the lineage crosswalk."""
    s = resolved.copy()
    s["_rank"] = s.source.map(SOURCE_PRIORITY)

    def first(g, col, by, asc=True):
        v = g.sort_values(by, ascending=asc)[col].dropna()
        v = v[v.astype(str) != ""]
        return v.iloc[0] if len(v) else None

    out = []
    for cid, g in s.groupby("customer_id"):
        out.append(dict(
            customer_id=cid,
            name_en=first(g, "name_en", "_rank"), name_ar=first(g, "name_ar", "_rank"),
            national_id=first(g, "national_id_std", "_rank"), date_of_birth=first(g, "dob", "_rank"),
            mobile=first(g, "mobile_std", "record_date", False), email=first(g, "email", "record_date", False),
            city=first(g, "city", "_rank"), segment=first(g, "segment", "_rank"),
            preferred_language=first(g, "preferred_language", "_rank"),
            casa_balance=g.casa_balance.sum(min_count=1), total_credit_limit=g.credit_limit.sum(min_count=1),
            card_outstanding=g.card_outstanding.sum(min_count=1),
            card_products=", ".join(sorted(g.card_product.dropna().unique())),
            source_systems=", ".join(sorted(g.source.unique())), source_system_count=g.source.nunique(),
            source_record_count=len(g)))
    gold = pd.DataFrame(out)
    gold["relationship_value"] = gold.casa_balance.fillna(0) + gold.total_credit_limit.fillna(0)
    xref = s[["customer_id", "record_key", "source", "source_id", "name_en", "mobile", "national_id", "dob_raw"]]
    return gold, xref


def run(t24, crm, cards, country_code="990", fuzzy_threshold=0.85):
    silver = standardize(t24, crm, cards, country_code)
    resolved, links = resolve(silver, fuzzy_threshold)
    gold, xref = build_golden(resolved)
    return dict(silver=resolved, gold=gold, xref=xref, links=links)


def evaluate(resolved, truth):
    """Compare clusters with ground truth: false merges (one golden record = several people) and missed matches."""
    t = resolved.merge(truth, on="record_key", how="left")
    false_merges = int((t.groupby("customer_id").person_id.nunique() > 1).sum())
    missed = int((t.groupby("person_id").customer_id.nunique() > 1).sum())
    return dict(source_records=len(t), golden_customers=t.customer_id.nunique(), true_customers=t.person_id.nunique(),
                false_merges=false_merges, missed_matches=missed)
