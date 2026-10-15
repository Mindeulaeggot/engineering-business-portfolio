# C++ orderbook and deterministic replay

Single-threaded educational limit-order matching engine. No exchange connectivity, market data feed, real capital or trading performance claim. Built with AI assistance for Minwoo Jeong's personal portfolio.

## Build and verify

Requires Python and a C++17 compiler. Run `python verify.py`; this compiles using `-Wall -Wextra -Werror -O2`, runs 16 named tests, checks 5,000 randomized commands with book invariants and deterministic replay, compares 2,000 further commands against an independently implemented Python linear-list matching oracle, then verifies identical output from two separate process replays. Generated results are in `reports/verification.json` and `reports/unit_test_results.txt`.

Run `orderbook.exe demo.commands` on Windows (or compile the two .cpp files for your platform). `engine.hpp` is the library API; `main.cpp` reads command journals and prints acknowledgements, trades and final state. The journal is input, not a crash-safe write-ahead log.

## Semantics

Prices are positive integer ticks. Quantities are positive integers. Sorted maps index price levels; linked lists maintain FIFO within a level; a hash index finds live orders. A lookup is average O(1), while level creation/removal is O(log P); matching costs depend on levels/orders consumed. This is not a universal O(1) or low-latency benchmark claim.

Trades execute at resting maker price with partial fills. All replacements lose time priority, even quantity reductions. Invalid replacements leave the old order intact. IDs may not be reused after fill/cancel. Self-trade prevention cancels resting same-account orders. Kill switch blocks new orders and replacements, but allows cancellations.

Limits are per-order quantity, price and notional, not aggregate account exposure, margin or regulatory risk checks. No market orders, decimal parsing, multi-instrument routing, persistent positions or concurrent matching are implemented.

## Command format

```
ADD id account B|S integer_price integer_quantity
CANCEL id
REPLACE id integer_price integer_quantity
KILL 0|1
```

The deterministic command stream enables exact replay. Rejected commands are printed with reasons; snapshots include the kill-switch state. The independent oracle tests ADD/matching behavior; named tests cover cancellation, replacement, risk limits, parsing and kill switch. Randomized checks are not proof of correctness for every input or exception.

## Next steps

Add a crash-safe sequenced event log, property-based tests against a richer reference, aggregate account exposure controls and failure-recovery semantics. Only then investigate profiling, allocator choices and concurrency. Do not claim production exchange readiness.

