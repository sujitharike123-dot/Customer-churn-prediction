### Churn rate by contract type (CTE + window function ranking)

| Contract       |   customers |   churned |   churn_rate_pct |   avg_monthly_charges |   risk_rank |
|:---------------|------------:|----------:|-----------------:|----------------------:|------------:|
| Month-to-month |        3875 |      1655 |             42.7 |                 66.4  |           1 |
| One year       |        1473 |       166 |             11.3 |                 65.05 |           2 |
| Two year       |        1695 |        48 |              2.8 |                 60.77 |           3 |

### Churn rate by tenure band with running share of all churners

| tenure_band     |   customers |   churned |   churn_rate_pct |   cumulative_pct_of_churners |
|:----------------|------------:|----------:|-----------------:|-----------------------------:|
| 1) 0-5 months   |        1371 |       744 |             54.3 |                         39.8 |
| 2) 6-11 months  |         698 |       255 |             36.5 |                         53.5 |
| 3) 12-23 months |        1047 |       309 |             29.5 |                         70   |
| 4) 24-47 months |        1624 |       339 |             20.9 |                         88.1 |
| 5) 48+ months   |        2303 |       222 |              9.6 |                        100   |

### Highest-churn segments (contract x internet service) with at least 100 customers

| Contract       | InternetService   |   customers |   churn_rate_pct |   monthly_revenue_lost |
|:---------------|:------------------|------------:|-----------------:|-----------------------:|
| Month-to-month | Fiber optic       |        2128 |             54.6 |                 100482 |
| Month-to-month | DSL               |        1223 |             32.2 |                  18367 |
| One year       | Fiber optic       |         539 |             19.3 |                  10572 |
| Month-to-month | No                |         524 |             18.9 |                   1998 |
| One year       | DSL               |         570 |              9.3 |                   3356 |

### Does tech support reduce churn? (self-join of two segment aggregates)

| segment   |   customers |   churn_rate_pct |   pts_vs_with_support |
|:----------|------------:|-----------------:|----------------------:|
| No        |        3473 |             41.6 |                  26.4 |
| Yes       |        2044 |             15.2 |                   0   |

