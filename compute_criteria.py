#!/usr/bin/env python3
"""Phase A.3 — Compute criteria 1 and 2 on TRAIN panel."""
import json
import math
from pathlib import Path

try:
    from scipy.stats import fisher_exact
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False


def wilson_ci(k: int, n: int, alpha: float = 0.05) -> tuple[float, float]:
    """Wilson 1927 CI for proportion. Pure Python (no scipy needed)."""
    if n == 0:
        return (0.0, 1.0)
    z = 1.959963984540054  # z_{1-alpha/2} for alpha=0.05
    p_hat = k / n
    denom = 1 + z**2 / n
    center = p_hat + z**2 / (2 * n)
    margin = z * math.sqrt(p_hat * (1 - p_hat) / n + z**2 / (4 * n**2))
    lower = (center - margin) / denom
    upper = (center + margin) / denom
    return (lower, upper)


def main():
    results = [json.loads(line) for line in open("results_train.jsonl") if line.strip()]
    ok = [r for r in results if r["status"] == "ok"]
    skipped = [r for r in results if r["status"] == "skip"]

    print(f"=== Phase A.3 — TRAIN panel results ===")
    print(f"N_total = {len(results)}, N_ok = {len(ok)}, N_skipped = {len(skipped)}")
    if skipped:
        print(f"Skipped (pre-registered SKIP_REASONS):")
        for r in skipped:
            print(f"  - {r['bug_id']}: {r.get('skip_reason', '?')}")
    print()

    n = len(ok)
    forge_top10 = sum(1 for r in ok if r.get("in_top_10"))
    random_top10 = sum(1 for r in ok if r.get("random_baseline_rank", 999) <= 10)
    forge_top3 = sum(1 for r in ok if r.get("rank_carmack") and r["rank_carmack"] <= 3)
    forge_top5 = sum(1 for r in ok if r.get("rank_carmack") and r["rank_carmack"] <= 5)
    forge_top30 = sum(1 for r in ok if r.get("rank_carmack") and r["rank_carmack"] <= 30)

    predict_top10 = sum(1 for r in ok if r.get("rank_predict") and r["rank_predict"] <= 10)

    print(f"=== Top-K hits ===")
    print(f"  carmack:  top3={forge_top3}/{n}  top5={forge_top5}/{n}  top10={forge_top10}/{n}  top30={forge_top30}/{n}")
    print(f"  predict:  top10={predict_top10}/{n}")
    print(f"  random:   top10={random_top10}/{n}")
    print()

    # === CRITÈRE 1 — forge bat le hasard (Fisher exact) ===
    print(f"=== CRITÈRE 1 — Fisher exact (forge_top10 vs random_top10) ===")
    table = [[forge_top10, n - forge_top10],
             [random_top10, n - random_top10]]
    print(f"  Contingency table: {table}")
    if HAS_SCIPY:
        odds_ratio, p_value = fisher_exact(table)
        print(f"  Fisher exact two-sided: p = {p_value:.4f}, odds_ratio = {odds_ratio:.2f}")
        c1_pass = (p_value < 0.05) and (forge_top10 > random_top10)
    else:
        p_value = None
        c1_pass = forge_top10 > random_top10  # weakened without scipy
    threshold_c1 = "p < 0.05 AND forge_hits > random_hits"
    verdict_c1 = "OUI" if c1_pass else "NON"
    print(f"  Threshold: {threshold_c1}")
    print(f"  VERDICT C1: {verdict_c1}  (p={p_value:.4f}, forge={forge_top10} vs random={random_top10})")
    print()

    # === CRITÈRE 2 — precision@10 ≥ 0.50, Wilson CI lower ≥ 0.30 ===
    print(f"=== CRITÈRE 2 — precision@10 + Wilson CI ===")
    p10 = forge_top10 / n if n else 0.0
    wilson_low, wilson_high = wilson_ci(forge_top10, n)
    print(f"  precision@10 = {forge_top10}/{n} = {p10:.4f}")
    print(f"  Wilson 95% CI = [{wilson_low:.4f}, {wilson_high:.4f}]")
    threshold_c2 = "precision@10 ≥ 0.50 AND wilson_low ≥ 0.30"
    c2_pass = (p10 >= 0.50) and (wilson_low >= 0.30)
    verdict_c2 = "OUI" if c2_pass else "NON"
    print(f"  Threshold: {threshold_c2}")
    print(f"  VERDICT C2: {verdict_c2}")
    print()

    # === Per-bucket breakdown ===
    print(f"=== Per-bucket precision@10 ===")
    for bucket in ["small", "medium", "large"]:
        sub = [r for r in ok if r["bucket"] == bucket]
        if sub:
            hits = sum(1 for r in sub if r.get("in_top_10"))
            print(f"  {bucket:6}: {hits}/{len(sub)} = {hits/len(sub):.2f}")
        else:
            print(f"  {bucket:6}: empty (N=0)")
    print()

    # === Per-project breakdown ===
    print(f"=== Per-project breakdown ===")
    by_proj = {}
    for r in ok:
        by_proj.setdefault(r["project"], []).append(r)
    for proj, lst in by_proj.items():
        ranks = [r.get("rank_carmack", "N/A") for r in lst]
        print(f"  {proj:15}: ranks={ranks}, total_files={[r['total_files'] for r in lst]}")
    print()

    # Save summary
    summary = {
        "n_total": len(results),
        "n_ok": n,
        "n_skipped": len(skipped),
        "skipped_ids": [r["bug_id"] for r in skipped],
        "forge_top10": forge_top10,
        "random_top10": random_top10,
        "predict_top10": predict_top10,
        "precision_at_3": forge_top3 / n if n else 0,
        "precision_at_5": forge_top5 / n if n else 0,
        "precision_at_10": p10,
        "precision_at_30": forge_top30 / n if n else 0,
        "wilson_ci_low": wilson_low,
        "wilson_ci_high": wilson_high,
        "fisher_p_value": p_value,
        "verdict_c1": verdict_c1,
        "verdict_c2": verdict_c2,
    }
    Path("phase_a3_summary.json").write_text(json.dumps(summary, indent=2))
    print(f"Summary saved to phase_a3_summary.json")


if __name__ == "__main__":
    main()
