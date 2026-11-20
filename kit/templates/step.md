# StepNN · <name>

## Sub-tasks (at least 3)
- [ ] NN.1 <input → output, data format, how it is checked>
- [ ] NN.2
- [ ] NN.3

## Audit-ready limits
Auditors attack every gap in a spec with the most extreme input they can imagine.
Write the real limits as numbers and say what happens outside them.
- Inputs: <field: min..max, max length, max count; outside → ignore / default / "unknown">
- Time: <timeouts in seconds, clock used, how far in the future a timestamp may be>
- Concurrency and processes: <max workers, kill-tree deadline>
- Nothing beyond these limits is handled. Findings about inputs outside them are out of scope.

## Contract
- Input:
- Output:

## Acceptance
- Tests: <what the asserts check>
- Lint: `python kit/rsh_lint.py check .` → 0 issues
- Audit: `python kit/rsh_audit.py --spec steps/stepNN.md --files <changed files>` → exit 0
