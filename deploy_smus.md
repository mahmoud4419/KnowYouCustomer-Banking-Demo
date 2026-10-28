# Deploy on Amazon SageMaker Unified Studio (~20 minutes)

1. **Project.** Create or open a SMUS project with a JupyterLab space. Note the project's Glue database,
   S3 location and **Athena workgroup** (the default `primary` workgroup is usually not permitted for project roles).
2. **Upload.** Upload `src/`, `notebooks/` and `data/sample/` keeping the repo layout, or upload the CSVs to the project's
   S3 location and point `DATA_DIR` at that `s3://` prefix.
3. **Configure.** In the first cell of each notebook set `DATA_DIR`, `DATABASE`, `S3_PATH`, `WORKGROUP`, `REGION`,
   `MODEL_ID`. Set `PUBLISH = True` to write Iceberg tables to the catalog.
4. **Bedrock.** Enable a text model in the Bedrock console. The default is `us.amazon.nova-pro-v1:0`
   (a cross-region inference profile). If you use another model, keep the `us.` inference-profile prefix where required.
   The project role needs `bedrock:InvokeModel`.
5. **Run All** on `01_customer360_mdm.ipynb`, then `02_fraud_detection.ipynb`.

## Troubleshooting
| Error | Fix |
|---|---|
| `FileNotFoundError: data/...` | `DATA_DIR` is a local path. If the CSVs are in S3, use the full `s3://` prefix. |
| `AccessDeniedException ... athena:GetWorkGroup` | Set `WORKGROUP` to the project's Athena workgroup. |
| `ResourceNotFoundException ... end of its life` | The Bedrock model was retired; set `MODEL_ID` to a current model. |
| `AccessDeniedException` on Bedrock | Enable model access, or add `bedrock:InvokeModel` to the project role. |
| `ModuleNotFoundError: awswrangler` | `%pip install awswrangler` and restart the kernel. |
| Project creation fails: SageMaker `Total domains` limit | Each project's tooling environment creates a SageMaker AI domain; delete unused ones or request a quota increase. |
