# Service health and incident monitor

A local Python backend with SQLite persistence, a read-only JSON API and a vanilla-JavaScript dashboard. Built with AI assistance for Minwoo Jeong's personal portfolio, inspired by network support work but using **no employer/customer logs or private infrastructure**.

## Run

Python standard library only. `python -m unittest -v test_monitor` runs 15 state, persistence and local HTTP integration tests.

Generate a new synthetic demo database (choose a fresh path; existing files are never replaced):

```
python monitor.py --demo --db demo.sqlite
python monitor.py --db demo.sqlite --port 8765
```

Open http://127.0.0.1:8765. To monitor the local health endpoint every five seconds:

```
python monitor.py --db live.sqlite --target http://127.0.0.1:8765/health --port 8765
```

Stop with Ctrl+C. The server binds to loopback only. `/health`, `/api/status`, `/api/incidents` and `/` are available; unknown routes return 404. No arbitrary target can be submitted through the API. Public/DNS targets and redirects are blocked; the probe bypasses proxy configuration. This is a local demo, not a public authenticated monitoring platform.

## State and persistence

Two consecutive failed samples confirm an incident; two healthy samples confirm recovery. A single failure does not page/open an incident. State, samples and transitions commit in one SQLite transaction; a unique partial index prevents multiple open incidents per target. Per-target timestamps must increase. Restarting reuses saved failure streaks and incidents. Records use parameterized SQL; dashboard values use textContent rather than HTML interpolation.

Incident start is the first sample in a confirmed failure streak; close is the second recovery-confirming sample. The span includes confirmation delay and is **not exact outage duration**. Healthy-sample ratios are not continuous-time uptime or contractual SLA. The deterministic demo has twelve synthetic samples across two targets and two closed incidents. There is no alert dispatch, authentication, data-retention job, distributed coordination or customer monitoring.

## Tests and next steps

Tests cover thresholding, flapping, duplicate-open prevention, restart persistence, invalid timestamps/latencies, target isolation, forbidden probes and real local HTTP responses. Next steps are configurable retention, stale-sample states, structured logs, authentication before any non-loopback use, asynchronous probing at larger scale and explicit SLO-window semantics.
