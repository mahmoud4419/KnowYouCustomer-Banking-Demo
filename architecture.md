# Architecture

```mermaid
flowchart LR
  subgraph Sources
    CB[Core banking]:::s
    CRM[CRM]:::s
    CARDS[Cards]:::s
    TX[Transaction stream]:::s
  end
  subgraph Lakehouse["Amazon S3 + Apache Iceberg (AWS Glue Data Catalog)"]
    B[Bronze: raw extracts] --> S[Silver: canonical schema]
    S --> IR[Identity resolution\ndeterministic + fuzzy]
    IR --> G[Gold: golden record\n+ lineage crosswalk]
  end
  CB --> B
  CRM --> B
  CARDS --> B
  G --> FEAT[Customer-level fraud features]
  TX --> FEAT
  FEAT --> SC[Rules + ML score\nAPPROVE / STEP_UP / BLOCK]
  SC --> Q[Alert queue]
  G --> BR[Amazon Bedrock\nbilingual briefing]
  Q --> CN[Amazon Bedrock\ncase narrative]
  G --> BI[Athena / QuickSight]
  classDef s fill:#eef3fb,stroke:#3e6fb0
```

| Layer | Demo | Production |
|---|---|---|
| Ingestion | CSV extracts | AWS DMS (CDC), Amazon MSK / Kinesis, AppFlow |
| Storage | Iceberg tables via Athena | Iceberg on S3 / S3 Tables, Glue Data Catalog |
| Identity resolution | pandas (this repo) | AWS Glue / EMR Spark, or AWS Entity Resolution |
| Fraud scoring | numpy logistic regression + rules | SageMaker real-time endpoint, Managed Flink features |
| Governance | — | AWS Lake Formation (row/column security, masking) |
| GenAI | Amazon Bedrock Converse API | Bedrock with Guardrails |
