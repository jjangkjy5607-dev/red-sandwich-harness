# Step01 - Ship paid Korean orders

## Contract
- Input: list of order dicts with `id`, `paid` (bool), `country` (ISO code), `total` (int, KRW, 0..10,000,000).
- Output: list of carrier responses for orders that are paid, country `KR`, total > 0.
- A carrier `ConnectionError` must not stop the batch; it is logged as `order <id>: <error>`.

## Audit-ready limits
- Orders per call: 0..5,000. Values outside the contract are ignored, not repaired.
