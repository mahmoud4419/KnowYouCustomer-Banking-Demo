"""Synthetic, deliberately messy multi-system banking data (fictional Lumora Bank).

Generates three source-system extracts that describe the same customers inconsistently
(core banking, CRM, cards), a ground-truth mapping, and a card/transfer transaction
stream with injected fraud patterns.
"""
import random
import datetime as dt
import numpy as np
import pandas as pd

FIRST = [("Mohammed", ["Mohamed", "Muhammad", "Mohamad"], "محمد"), ("Ahmed", ["Ahmad", "Ahmet"], "أحمد"),
         ("Fatima", ["Fatma", "Fatemah"], "فاطمة"), ("Khalid", ["Khaled", "Khalied"], "خالد"),
         ("Aisha", ["Ayesha", "Aysha"], "عائشة"), ("Omar", ["Umar", "Omer"], "عمر"),
         ("Mariam", ["Maryam", "Miriam"], "مريم"), ("Hamad", ["Hamed", "Hammad"], "حمد"),
         ("Noura", ["Nora", "Nourah"], "نورة"), ("Saeed", ["Said", "Saed"], "سعيد"),
         ("Yousef", ["Youssef", "Yusuf"], "يوسف"), ("Layla", ["Laila", "Leila"], "ليلى"),
         ("Rashid", ["Rashed", "Rasheed"], "راشد"), ("Huda", ["Hoda", "Houda"], "هدى"), ("Sultan", ["Soltan"], "سلطان")]
LAST = [("Al Mansoori", ["Almansouri", "Al-Mansouri", "Mansoori"], "المنصوري"), ("Al Nuaimi", ["Alnuaimi", "Al-Noaimi"], "النعيمي"),
        ("Al Shamsi", ["Alshamsi", "Al-Shamsy"], "الشامسي"), ("Al Hashimi", ["Alhashemi", "Al-Hashmi"], "الهاشمي"),
        ("Al Ketbi", ["Alkatbi", "Al-Kitbi"], "الكتبي"), ("Al Zaabi", ["Alzaabi", "Al-Za'abi"], "الزعابي"),
        ("Al Marzouqi", ["Almarzooqi", "Al-Marzouki"], "المرزوقي"), ("Al Dhaheri", ["Aldhaheri", "Al-Daheri"], "الظاهري"),
        ("Khan", ["Kahn"], "خان"), ("Haddad", ["Hadad"], "حداد"), ("Al Suwaidi", ["Alsuwaidi", "Al-Suwaydi"], "السويدي"),
        ("Al Balushi", ["Albloushi", "Al-Blooshi"], "البلوشي")]
CITIES = ["Al Noor City", "Riverside", "Palm Harbor", "Old Town", "Crescent Bay"]   # fictional
FOREIGN = [("BB", "Port Avalon"), ("CC", "Northgate"), ("DD", "Silverton")]           # fictional
HOME_COUNTRY = "AA"
MCC = ["grocery", "fuel", "restaurants", "electronics", "fashion", "travel", "utilities", "pharmacy"]


def _phone(m, style, cc):
    return {0: f"+{cc}{m}", 1: f"0{m}", 2: f"00{cc}{m}", 3: f"+{cc} {m[:2]} {m[2:5]} {m[5:]}", 4: f"{cc}-{m}"}[style]


def generate_customers(n_customers=200, n_lookalikes=8, seed=42, country_code="990"):
    """Return (t24, crm, cards, truth, persons). truth maps record_key -> person_id."""
    rnd = random.Random(seed)
    persons = []
    for i in range(n_customers):
        f, l = rnd.choice(FIRST), rnd.choice(LAST)
        dob = dt.date(1960, 1, 1) + dt.timedelta(days=rnd.randint(0, 15000))
        persons.append(dict(pid=i, f=f, l=l, dob=dob,
                            nid=f"{country_code}-{dob.year}-{rnd.randint(1000000, 9999999)}-{rnd.randint(1, 9)}",
                            mob=f"5{rnd.choice([0, 2, 4, 5, 6, 8])}{rnd.randint(1000000, 9999999)}",
                            email=f"{f[0].lower()}.{l[0].replace(' ', '').lower()}{rnd.randint(1, 99)}@"
                                  f"{rnd.choice(['mail.example', 'inbox.example', 'post.example'])}",
                            city=rnd.choice(CITIES)))
    t24, crm, cards, truth = [], [], [], []
    for p in persons:
        cif = f"CIF{100000 + p['pid']}"
        p["cif"] = cif
        t24.append(dict(cif_id=cif, full_name=f"{p['f'][0]} {p['l'][0]}", date_of_birth=p["dob"].isoformat(),
                        national_id=p["nid"], mobile=_phone(p["mob"], 0, country_code), city=p["city"],
                        segment=rnd.choice(["Retail", "Priority", "Youth"]),
                        casa_balance=round(rnd.uniform(500, 450000), 2),
                        last_updated=(dt.date(2026, 1, 1) + dt.timedelta(days=rnd.randint(0, 280))).isoformat()))
        truth.append((f"T24:{cif}", p["pid"]))
        if rnd.random() < 0.85:
            cid = f"CRM-{5000 + p['pid']}"
            nm = (f"{rnd.choice(p['f'][1]) if rnd.random() < 0.6 else p['f'][0]} "
                  f"{rnd.choice(p['l'][1]) if rnd.random() < 0.6 else p['l'][0]}")
            crm.append(dict(contact_id=cid, name_en=nm, name_ar=f"{p['f'][2]} {p['l'][2]}",
                            national_id=(p["nid"] if rnd.random() < 0.5 else p["nid"].replace("-", "")) if rnd.random() < 0.6 else "",
                            mobile=_phone(p["mob"], rnd.choice([1, 2, 3]), country_code),
                            email=p["email"] if rnd.random() < 0.9 else p["email"].upper(),
                            date_of_birth=p["dob"].strftime("%d/%m/%Y") if rnd.random() < 0.8 else "",
                            preferred_language=rnd.choice(["ar", "en"]),
                            last_contact_date=(dt.date(2026, 3, 1) + dt.timedelta(days=rnd.randint(0, 230))).isoformat()))
            truth.append((f"CRM:{cid}", p["pid"]))
        p["card"] = None
        if rnd.random() < 0.6:
            k = f"CARD-{900000 + p['pid']}"
            p["card"] = k
            holder = (f"{(rnd.choice(p['f'][1]) if rnd.random() < 0.5 else p['f'][0]).upper()} "
                      f"{(rnd.choice(p['l'][1]) if rnd.random() < 0.5 else p['l'][0]).upper()}")
            cards.append(dict(card_account_id=k, cardholder_name=holder,
                              mobile=_phone(p["mob"], rnd.choice([2, 4]), country_code) if rnd.random() < 0.9 else "",
                              date_of_birth=p["dob"].strftime("%Y%m%d"),
                              card_product=rnd.choice(["Platinum Credit", "Signature Credit", "Debit Classic", "Infinite Credit"]),
                              credit_limit=rnd.choice([0, 10000, 25000, 50000, 100000]),
                              outstanding=round(rnd.uniform(0, 20000), 2),
                              email=p["email"] if rnd.random() < 0.5 else ""))
            truth.append((f"CARDS:{k}", p["pid"]))
    # look-alikes: same name as an existing customer, different person (tests over-merging)
    for j in range(n_lookalikes):
        p0 = persons[j]
        dob = p0["dob"] + dt.timedelta(days=4000)
        cif = f"CIF{900000 + j}"
        t24.append(dict(cif_id=cif, full_name=f"{p0['f'][0]} {p0['l'][0]}", date_of_birth=dob.isoformat(),
                        national_id=f"{country_code}-{dob.year}-{rnd.randint(1000000, 9999999)}-{rnd.randint(1, 9)}",
                        mobile=f"+{country_code}5{rnd.randint(10000000, 99999999)}", city=rnd.choice(CITIES),
                        segment="Retail", casa_balance=round(rnd.uniform(500, 90000), 2), last_updated="2026-05-01"))
        truth.append((f"T24:{cif}", 1000 + j))
        persons.append(dict(pid=1000 + j, cif=cif, card=None, city=rnd.choice(CITIES)))
    truth = pd.DataFrame(truth, columns=["record_key", "person_id"])
    return pd.DataFrame(t24), pd.DataFrame(crm), pd.DataFrame(cards), truth, persons


def generate_transactions(persons, days=60, start="2026-08-01", fraud_victim_rate=0.08, seed=7):
    """Card / transfer transactions keyed by source-system account (account_ref = 'SOURCE:id')."""
    rnd = random.Random(seed)
    nrng = np.random.default_rng(seed)
    t0 = pd.Timestamp(start)
    rows, n = [], 0

    def add(p, ts, amount, channel, mcc, country, city, device, account, fraud):
        nonlocal n
        n += 1
        rows.append(dict(txn_id=f"TX{n:07d}", account_ref=account, ts=ts.isoformat(), amount=round(float(amount), 2),
                         channel=channel, merchant_category=mcc, merchant_country=country, city=city,
                         device_id=device, is_fraud=int(fraud)))

    for p in persons:
        accounts = [f"T24:{p['cif']}"] + ([f"CARDS:{p['card']}"] if p.get("card") else [])
        devices = [f"DEV-{p['pid']:05d}-A"]
        scale = float(nrng.lognormal(5.0, 0.6))
        for _ in range(rnd.randint(25, 55)):
            ts = t0 + pd.Timedelta(days=rnd.uniform(0, days))
            ts = ts.normalize() + pd.Timedelta(hours=rnd.choice(range(7, 24)) if rnd.random() > 0.04 else rnd.randint(0, 5),
                                               minutes=rnd.randint(0, 59))
            account = rnd.choice(accounts)
            channel = (rnd.choice(["card_pos", "card_pos", "card_online", "atm"]) if account.startswith("CARDS")
                       else rnd.choice(["transfer", "atm", "transfer"]))
            amount = float(nrng.lognormal(np.log(scale), 0.7)) * (6 if rnd.random() < 0.02 else 1)
            country, city = HOME_COUNTRY, p["city"]
            if rnd.random() < 0.06:                      # legit travel, sometimes big-ticket and late
                country, city = rnd.choice(FOREIGN)
                if rnd.random() < 0.35:
                    amount *= rnd.uniform(3, 8)
                    ts = ts.normalize() + pd.Timedelta(hours=rnd.choice([0, 1, 2, 23]), minutes=rnd.randint(0, 59))
            if rnd.random() < 0.01:                      # legit big purchase at home
                amount *= rnd.uniform(5, 10)
            if rnd.random() < 0.02 and len(devices) == 1:  # legit new phone
                devices.append(f"DEV-{p['pid']:05d}-B")
            add(p, ts, amount, channel, rnd.choice(MCC), country, city, devices[-1], account, False)
        if rnd.random() < fraud_victim_rate:            # account takeover / card-not-present burst
            account = accounts[-1]
            ts = t0 + pd.Timedelta(days=rnd.uniform(5, days - 1))
            ts = ts.normalize() + pd.Timedelta(hours=rnd.choice([1, 2, 3, 4, 22, 23]), minutes=rnd.randint(0, 59))
            stealth = rnd.random() < 0.4                 # stealthy: home country, known device, modest amounts
            country, city = (HOME_COUNTRY, rnd.choice(CITIES)) if stealth else rnd.choice(FOREIGN)
            device = devices[-1] if stealth else f"DEV-UNK-{rnd.randint(10000, 99999)}"
            for _ in range(rnd.randint(2, 6)):
                ts = ts + pd.Timedelta(minutes=rnd.randint(2, 25))
                add(p, ts, scale * rnd.uniform(1.5, 6) if stealth else scale * rnd.uniform(3, 15),
                    "card_online" if account.startswith("CARDS") else "transfer",
                    rnd.choice(["electronics", "travel", "fashion"]), country, city, device, account, True)
    df = pd.DataFrame(rows).sort_values("ts").reset_index(drop=True)
    return df
