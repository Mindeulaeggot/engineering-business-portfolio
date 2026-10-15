# Campaign budget prioritization

Business question: with a limited contact budget, does a complex scoring model justify a prospective pilot over a simple prior-success rule?

## Run

Install the parent requirements. Run `python analysis.py`, then `python -m unittest -v test_analysis` from this folder. Inspect `reports/executive_brief.html`, `reports/metrics.json`, `reports/budget_curve.csv` and `reports/holdout_scores.csv`.

## Design

Uses the 41,188-record `bank-additional-full.csv`, ordered by date per UCI documentation. First 60% trains, next 20% selects between logistic regression and Random Forest by average precision, final 20% is held out. Models are not refit on test outcomes. Budget fractions 10%, 20%, 30%, 50% and 100% are fixed in advance. A simple prior-success rule uses seeded random tie-breaking inside its two tiers; the random baseline is the test prevalence expectation. These are not guaranteed optimal strategies.

Post-call duration and current-campaign contact count are excluded. Demographic and credit fields are excluded from scoring, but this does not establish fairness: other fields may proxy protected attributes. Planned contact timing/type and macro variables must be available at scoring time. Records describe a historically selected, contacted population; there are no customer identifiers or randomized no-contact controls. Temporal change is substantial and individual customers may repeat across periods.

## What the result means

The selected model's 20%-budget holdout precision is **36.3%**, below the simple prior-success rule's **56.2%**. The positive rate also changes from **4.8%** in training to **30.8%** in test. This is evidence of deployment risk and the value of simple baselines, not an ML success claim. The business brief recommends a prospective randomized pilot and drift/fairness checks before use.

Nine financial scenarios assume contribution of 20/50/100 and contact costs of 1/3/5 arbitrary currency units. They are accounting illustrations on observed labels, **not causal uplift, incremental deposits, realized profit or calibrated customer lifetime value**. Removing post-call leakage does not remove selection bias.

## Next steps

Obtain exact dates and customer IDs, evaluate multiple out-of-time windows, validate probability calibration prospectively, establish consent/fairness controls and compare incremental outcomes in a randomized pilot. Do not deploy to allocate real financial products from this prototype.

Source: Moro, Rita and Cortez (2014), Bank Marketing, UCI, CC BY 4.0, https://doi.org/10.24432/C5K306. Built with AI assistance for Minwoo Jeong's personal portfolio.

