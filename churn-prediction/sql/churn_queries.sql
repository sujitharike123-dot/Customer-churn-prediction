-- Queries below run against the `customers` table (loaded into SQLite by src/churn_analysis.py).
-- Each one is introduced by a title comment line.

-- QUERY: Churn rate by contract type (CTE + window function ranking)
WITH by_contract AS (
    SELECT Contract,
           COUNT(*)                               AS customers,
           SUM(Churn)                             AS churned,
           ROUND(100.0 * SUM(Churn) / COUNT(*), 1) AS churn_rate_pct,
           ROUND(AVG(MonthlyCharges), 2)          AS avg_monthly_charges
    FROM customers
    GROUP BY Contract
)
SELECT Contract, customers, churned, churn_rate_pct, avg_monthly_charges,
       RANK() OVER (ORDER BY churn_rate_pct DESC) AS risk_rank
FROM by_contract
ORDER BY risk_rank;

-- QUERY: Churn rate by tenure band with running share of all churners
WITH banded AS (
    SELECT CASE WHEN tenure < 6  THEN '1) 0-5 months'
                WHEN tenure < 12 THEN '2) 6-11 months'
                WHEN tenure < 24 THEN '3) 12-23 months'
                WHEN tenure < 48 THEN '4) 24-47 months'
                ELSE                  '5) 48+ months' END AS tenure_band,
           Churn
    FROM customers
),
agg AS (
    SELECT tenure_band, COUNT(*) AS customers, SUM(Churn) AS churned,
           ROUND(100.0 * SUM(Churn) / COUNT(*), 1) AS churn_rate_pct
    FROM banded GROUP BY tenure_band
)
SELECT tenure_band, customers, churned, churn_rate_pct,
       ROUND(100.0 * SUM(churned) OVER (ORDER BY tenure_band) / SUM(churned) OVER (), 1) AS cumulative_pct_of_churners
FROM agg
ORDER BY tenure_band;

-- QUERY: Highest-churn segments (contract x internet service) with at least 100 customers
SELECT Contract, InternetService,
       COUNT(*)                                AS customers,
       ROUND(100.0 * SUM(Churn) / COUNT(*), 1) AS churn_rate_pct,
       ROUND(SUM(CASE WHEN Churn = 1 THEN MonthlyCharges ELSE 0 END), 0) AS monthly_revenue_lost
FROM customers
GROUP BY Contract, InternetService
HAVING COUNT(*) >= 100
ORDER BY churn_rate_pct DESC
LIMIT 5;

-- QUERY: Does tech support reduce churn? (self-join of two segment aggregates)
WITH seg AS (
    SELECT TechSupport, COUNT(*) AS customers,
           ROUND(100.0 * SUM(Churn) / COUNT(*), 1) AS churn_rate_pct
    FROM customers
    WHERE InternetService <> 'No'
    GROUP BY TechSupport
)
SELECT a.TechSupport AS segment, a.customers, a.churn_rate_pct,
       ROUND(a.churn_rate_pct - b.churn_rate_pct, 1) AS pts_vs_with_support
FROM seg a
JOIN seg b ON b.TechSupport = 'Yes'
ORDER BY a.churn_rate_pct DESC;
