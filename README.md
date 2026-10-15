# Personal portfolio projects

Four new, executable portfolio prototypes for Minwoo Jeong. Built with AI assistance in October 2026. These are personal projects, not employer deployments, client engagements, trading profits or independently verified evidence of proficiency. Read and reproduce the implementations before discussing them in interviews.

## Reproduce

Use Python 3.12 and a C++17 compiler (g++ on PATH). From this folder:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python run_all.py
```

The analytics commands download two small archives from the official UCI repository on first execution; subsequent runs reuse the local archives. SHA-256 hashes and split sizes are recorded in the result JSON. Raw datasets, temporary dependencies and executables are not intended for version control. All four projects run locally; none connects to a broker, places real trades, changes routing or scans a customer network.

## Projects and deliverables

| Project | Purpose | Entry point | Evidence |
|---|---|---|---|
| Campaign Budget Prioritization | Business decision and model-risk assessment | `campaign_budget/analysis.py` | Executive brief, budget curve, held-out scores, 10 tests |
| Demand and Service Capacity Planning | Cost-sensitive operations planning | `capacity_planning/analysis.py` | Executive brief, holdout capacity, scenario comparison, 9 tests |
| C++ Orderbook and Replay Engine | Data structures, order lifecycle, risk controls | `orderbook/verify.py` | 16 C++ tests, 5,000-command replay, independent 2,000-command oracle |
| Service Health and Incident Monitor | Backend API, SQLite state, failure handling | `service_monitor/monitor.py` | Dashboard, local HTTP API, persistence and integration tests |

HTML briefs are in the two analytics `reports` folders. `verification.json` records the full-suite result. Each project has its own README, test cases and limitations.

## Interview preparation

Explain the choices, not just the metrics. Campaign ranking did **not** beat a simple historical-success rule on the chronological test; the result is a reason to question deployment, not hide the baseline. Capacity savings are simulated costs, not actual savings. The orderbook is single-threaded and not exchange-ready. The monitor measures sampled health, not continuous uptime.

For each project, practice a five-minute walkthrough: question, implementation, baseline, test design, limitation, next step. Re-run the tests, modify one behavior and explain the diff before claiming working proficiency.

## Attribution and reuse

Bank Marketing: Moro, Rita and Cortez (2014), UCI, https://doi.org/10.24432/C5K306. Bike Sharing: Fanaee-T (2013), UCI, https://doi.org/10.24432/C5W894. Both source datasets are CC BY 4.0. Retain attribution when distributing data or derived aggregates. Implementation code was generated with AI assistance for this personal portfolio; do not imply that public data represents private banking customers or a current production system.

