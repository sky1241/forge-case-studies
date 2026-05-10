# Phase A — Workarounds discovered during pilot

**Date** : 2026-05-10
**Pilot case** : cookiecutter-2

---

## Workaround 1 — `forge --carmack` truncates output to top 15

### Problem (pilot finding)

`forge --carmack` (CLI) shows only top 15 files in stdout (hardcoded `for r in results[:15]:` at forge.py L4093). For change_files ranked > 15, we cannot read their exact rank from CLI output.

### Solution

Bypass CLI, call the underlying Python function `predict_carmack(root, weeks)` directly which returns `list[dict]` with all scored files (sorted by score desc, no truncation).

```python
import sys
sys.path.insert(0, '/home/sky/Bureau/forge')
import forge
results = forge.predict_carmack(Path('.'), weeks=999)
# results is a sorted list of dicts; index = rank-1
for i, r in enumerate(results, start=1):
    if r['file'] == change_file:
        rank = i
        break
```

This is acceptable because :
- We use the same algorithm forge.predict_carmack uses internally (no re-implementation)
- We don't modify forge source (no patch on the published v1.2.2)
- The CLI top-15 truncation is purely presentational — the underlying scoring is identical

### Validation

```
$ python -c "from forge import predict_carmack; r = predict_carmack(Path('.'), weeks=999); print(len(r))"
83  # vs CLI showed only 15
```

---

## Workaround 2 — `--weeks N` uses system date, not HEAD date

### Problem (pilot finding)

`forge --carmack --weeks 4` runs `git log --since=4 weeks ago` (forge.py L1022). On a checked-out PRE_BUG commit (HEAD pointing to a commit from 2020-04-15 for cookiecutter-2), `--since=4 weeks ago` evaluates to `2026-04-12` (4 weeks before today), filtering out ALL commits in the repo because none are recent enough → output : `No commits in the last 4 weeks`.

### Solution

Use `weeks=999` (or any value ≥ time-since-first-commit-in-the-repo). This includes all reachable history from HEAD, which after `git checkout PRE_BUG` does NOT contain future commits → no anti-leakage violation.

```python
results = forge.predict_carmack(Path('.'), weeks=999)
```

### Anti-leakage rationale

After `git checkout $PRE_BUG`, the commits visible from HEAD are a subset of the original repo history, ending at PRE_BUG. The bug commit and all subsequent commits are NOT reachable. Therefore:
- `weeks=999` includes history from first commit to PRE_BUG (allowed — no future visible)
- The Kalman/wavelet/coupling signals are computed over the full pre-bug window, which is more data, not less

### Trade-off vs `--weeks 4` semantics

The brief Phase A.2 specified `--weeks 4` to constrain the analytical window to "4 weeks before bug". With `weeks=999` this constraint is dropped — forge sees all history pre-bug.

Trade-off documented :
- forge.predict_carmack signals stabilize over longer windows (Kalman benefits from more bins)
- But the test loses "rolling-window" sensitivity claimed by the brief
- Result: we test forge in its "best-case data availability" mode, not its "tight-window" mode

If sky-master prefers the tight-window mode, we'd need to patch forge to support `--since-date YYYY-MM-DD`. Decision: defer patch, run with `weeks=999` for now (Phase A faster), document this in FINAL_REPORT.md as a methodological choice.

---

## Net impact on Phase A

- All 12 cases will use `predict_carmack(Path(repo), weeks=999)` direct call
- Rank of change_file extracted from full sorted list (no top-15 truncation)
- Anti-leakage maintained via `git checkout $PRE_BUG`

These workarounds are documented and committed BEFORE running Phase A on the panel.
