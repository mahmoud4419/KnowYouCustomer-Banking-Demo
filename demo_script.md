# 7-minute demo script

1. **The problem (45s).** Show the three raw extracts: one customer under three spellings, phone numbers in five
   formats, national IDs with and without dashes, three date formats.
2. **Golden record (2 min).** Run notebook 01. Show match links per rule, then the before/after for one customer:
   legal name from core banking, latest mobile from CRM, Arabic name, cards and total relationship value. Point out that
   look-alike customers with the same name stay separate.
3. **Why it matters for fraud (2 min).** Run notebook 02. Transactions arrive per account; the crosswalk links them to
   one customer, so velocity and anomaly features use the whole relationship. Show the metrics and the alert queue.
4. **Live score (30s).** Score one transaction with `fraud.score_one()`, the call a stream consumer makes.
5. **GenAI (1.5 min).** Bilingual relationship briefing, then the case narrative for the top alert, generated only
   from governed data.
6. **Close (15s).** Open Iceberg tables, governed lakehouse, built in days.
