# Lumora Bank — Customer 360 + Real-Time Fraud Detection on AWS

A runnable demo for a fictional digital bank, **Lumora Bank**. Three source systems (core banking, CRM, cards) describe
the same customers inconsistently. The demo builds a **golden customer record** (identity resolution / MDM through 360),
then uses that 360 view to **score transactions for fraud**, with Amazon Bedrock writing bilingual (English/Arabic)
relationship briefings and fraud case narratives.

All data is synthetic. Names, IDs, phone numbers, cities and country codes are fictional.

See [docs/architecture.md](docs/architecture.md) for the architecture diagram.

## What it shows
| Step | Outcome |
|---|---|
| Bronze | Raw extracts from 3 systems, inconsistent names, phone formats, ID formats and dates |
| Silver | One canonical schema; transliteration-tolerant name keys; standardized phones, IDs, dates |
| Gold | Deterministic (national ID, mobile, email) + fuzzy (name within same date of birth) matching → survivorship → golden record + lineage crosswalk |
| Fraud | Customer-level behavioral features (velocity, amount anomaly, new device, foreign merchant, night, online) → rules + logistic regression → APPROVE / STEP_UP / BLOCK |
| GenAI | Bedrock: bilingual relationship briefing per customer; case narrative for the top fraud alert |

## Results on the included sample data
- **Customer 360:** 503 source records → **208 golden customers** (ground truth 208), **0 false merges, 0 missed matches**, including 8 look-alike customers (same name, different person) that stay separate.
- **Fraud (time-based split, train on earlier days, test on later):** ROC AUC 0.982 (rules alone 0.938); the alert queue holds 58 of 2456 test transactions and catches 74% of fraud (19 cases), with precision 24%.

The fraud scenario deliberately includes hard cases: legitimate travel with large late-night purchases, and stealthy
fraud at home on a known device. Tune thresholds in `fraud.decide()` to trade recall for analyst workload.

## Quick start (local, no AWS needed)
```bash
pip install -r requirements.txt
python scripts/run_demo.py          # runs both pipelines on data/sample, writes output/*.csv
pytest -q                           # accuracy tests
jupyter lab notebooks/              # 01_customer360_mdm, 02_fraud_detection
```
The Bedrock cells need AWS credentials and model access; everything else runs offline.

## Run on Amazon SageMaker Unified Studio
See [docs/deploy_smus.md](docs/deploy_smus.md). In short: upload `src/`, `notebooks/` and `data/sample/` to the project,
set the config cell (data path, database, S3 path, Athena workgroup, Bedrock model), and Run All.

## Repository layout
```
src/lumora/      datagen.py · c360.py · fraud.py · genai.py · aws_io.py
notebooks/       01_customer360_mdm.ipynb · 02_fraud_detection.ipynb
scripts/         generate_data.py · run_demo.py
data/sample/     synthetic CSVs + ground truth
sql/             demo queries for Athena / SMUS query editor
docs/            architecture, SMUS deployment, demo script
tests/           pytest checks for matching accuracy and fraud separation
```

## Production notes
- The lakehouse tables are **Apache Iceberg** on Amazon S3 with the AWS Glue Data Catalog, so they stay readable by
  Spark, Athena, Redshift, Trino and other engines.
- At scale, run identity resolution as AWS Glue / EMR Spark jobs (or AWS Entity Resolution), serve the fraud model from
  a SageMaker real-time endpoint fed by Amazon MSK / Kinesis, and govern access with AWS Lake Formation.
- The matching rules here are a reference implementation for a demo, not a certified MDM engine.

## License
MIT for the code. Sample data is synthetic and may be reused freely.
