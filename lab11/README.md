# lab11

NYC 311, November 2025 — five questions about 304,905 service requests.

**Read the report: [report.md](report.md)**

| | |
|---|---|
| `report.md` | Findings, tables, every headline number with a verification column |
| `fig-borough-brooklyn.png` | Task 2 — Brooklyn's top ten complaint types |
| `fig-borough-per1000.png` | Task 3 — calls per 1,000 residents |
| `fig-hours.png` | Task 4 — noise vs heat, by hour of day |
| `fig-nights.png` | Task 4 — heat complaints, 30 days × 24 hours |
| `fig-same-job.png` | Task 5 — median hours to close HEAT/HOT WATER, by borough |
| `verify_output.txt` | 56/56 headline numbers agree across two independent code paths |

Data and the Census API key are **not** in this repository — see `.gitignore` and
§0 of the report for how to run it.

```bash
export CENSUS_API_KEY=...      # free key from api.census.gov/data/key_signup.html
python3 fetch_populations.py
python3 verify_all.py          # 56 checks, both methods
```
