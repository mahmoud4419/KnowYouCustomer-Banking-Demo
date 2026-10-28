-- Queries for the tables written with PUBLISH = True
SELECT 'source records' AS metric, COUNT(*) AS n FROM silver_customer_records
UNION ALL SELECT 'golden customers', COUNT(*) FROM gold_customer_360;

SELECT source_system_count, COUNT(*) AS customers FROM gold_customer_360 GROUP BY 1 ORDER BY 1;

-- one customer, every source record (lineage)
SELECT x.* FROM gold_customer_xref x
WHERE x.customer_id = (SELECT customer_id FROM gold_customer_360 WHERE source_system_count = 3
                       ORDER BY relationship_value DESC LIMIT 1)
ORDER BY x.source;

-- fraud alert queue joined to the golden record
SELECT f.ts, f.customer_id, g.name_en, g.segment, f.amount, f.channel, f.merchant_country, f.fraud_score, f.decision
FROM fraud_scored_txns f JOIN gold_customer_360 g USING (customer_id)
WHERE f.decision <> 'APPROVE' ORDER BY CAST(f.fraud_score AS double) DESC LIMIT 20;
