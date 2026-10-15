# Demand and service capacity planning

Business question: how should hypothetical hourly service throughput change when the assumed cost of unmet requests exceeds idle capacity cost?

## Run

Install the parent requirements. Run `python analysis.py` and `python -m unittest -v test_analysis`. Outputs: `reports/executive_brief.html`, `metrics.json`, `holdout_capacity.csv`, `scenario_comparison.csv`.

## Design

The downloaded UCI hourly CSV has **17,379 actual rows** (the repository landing-page instance metadata differs). Reconcile total rentals to registered plus casual rentals; verify unique hour timestamps. Missing recorded hours are not imputed as zero. Train before 2012-07-01, select quantile-tree complexity on July–September 2012, test on **2,168 recorded hours** from October–December 2012. Test is not used for tuning. A separate median model reports MAE; capacity policies are evaluated by asymmetric cost, not MAE alone.

Inputs are calendar fields and elapsed time. Exclude target components and actual weather, which would not be available without a weather forecast at planning time. Quantile targets are shortage cost / (shortage cost + idle cost), with ratios 2:1, 5:1, 10:1. Compare a constant quantile, hour/workday quantile and learned calendar quantile using the same training period.

## Results and boundaries

At the assumed **5:1** cost ratio, the learned policy has **29.45% lower modeled cost** than the hour/workday baseline on the final holdout. This is a retrospective scenario result, **not real savings or guaranteed future service improvement**. Inspect the complete sensitivity table and temporal drift before drawing conclusions.

Capacity is abstract hourly service throughput, **not the number of bikes needed**. Completed rentals are not latent demand; unavailable bikes can suppress observed rentals. No trip durations, station balances, physical fleet constraints or rebalancing costs are supplied. Actual fleet optimization cannot be inferred. Tree models do not extrapolate long-term growth reliably. No causal effect of weather or operational intervention is claimed.

## Next steps

Collect inventory, station/trip and lost-demand data; estimate real costs; evaluate rolling chronological windows; run shadow-mode capacity recommendations against the existing process with drift and coverage controls.

Source: Fanaee-T (2013), Bike Sharing, UCI, CC BY 4.0, https://doi.org/10.24432/C5W894. Built with AI assistance for Minwoo Jeong's personal portfolio.

