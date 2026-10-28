"""Read inputs from local disk or S3, and publish results to the Glue Data Catalog."""
import pandas as pd


def read_csv(path):
    if path.startswith("s3://"):
        import awswrangler as wr
        return wr.s3.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8")
    return pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8")


def publish(tables: dict, database: str, s3_path: str, workgroup: str = None):
    """Write each DataFrame as an Iceberg table via Athena; falls back to a Parquet table if Iceberg/Athena is blocked.
    In SageMaker Unified Studio, pass the project's Athena workgroup (the default 'primary' is usually not allowed)."""
    import awswrangler as wr
    for name, df in tables.items():
        df = df.astype({c: "string" for c in df.columns if df[c].dtype == object})
        try:
            wr.athena.to_iceberg(df=df, database=database, table=name, table_location=f"{s3_path}/lumora/{name}/",
                                 temp_path=f"{s3_path}/lumora/_tmp/{name}/", workgroup=workgroup, mode="overwrite")
            print(f"Iceberg  {database}.{name} ({len(df)} rows)")
        except Exception as e:  # noqa: BLE001
            print(f"Iceberg skipped for {name} ({type(e).__name__}); writing Parquet table")
            wr.s3.to_parquet(df=df, path=f"{s3_path}/lumora_parquet/{name}/", dataset=True, mode="overwrite",
                             database=database, table=name)
            print(f"Parquet  {database}.{name} ({len(df)} rows)")
