#!/usr/bin/env python3
"""Phase A — Run forge full power on each TRAIN case.

For each case in panel_train_seed42.json:
  1. Clone target repo (full, idempotent)
  2. Compute CUTOFF = BUG_DATE - 4 weeks
  3. Find PRE_BUG = last commit before CUTOFF
  4. git checkout PRE_BUG
  5. Verify change_file exists at PRE_BUG
  6. Call forge.predict_carmack(Path(repo), weeks=999) -> full ranked list
  7. Find rank of change_file in the list
  8. Run forge --modularity (CLI) -> parse Q
  9. Compute random_baseline_rank with seed=hash(bug_id)
 10. Append to results_train.jsonl

Hold-out is NOT touched (per sky-master directive: hold-out vierge until Phase B.3).
"""
import json
import math
import random
import re
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, '/home/sky/Bureau/forge')
import forge  # noqa: E402

ROOT = Path("/home/sky/forge-case-studies")
CLONES = ROOT / "clones"
FORGE_BIN = "/home/sky/Bureau/forge/.venv/bin/forge"
CUTOFF_WEEKS = 4

CLONES.mkdir(exist_ok=True)


def run(cmd, cwd=None, timeout=600, check=False):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                          timeout=timeout, check=check)


def clone_repo(github_url: str, project_name: str) -> Path:
    """Clone full (no shallow) so we have all commits for git rev-list."""
    target = CLONES / project_name
    if target.exists() and (target / ".git").exists():
        # Reset to default branch to undo previous PRE_BUG checkout
        run(["git", "reset", "--hard"], cwd=target)
        for branch in ("main", "master", "develop"):
            r = run(["git", "checkout", branch], cwd=target)
            if r.returncode == 0:
                break
        return target
    print(f"  CLONING {github_url} ...")
    r = run(["git", "clone", "--quiet", github_url, str(target)], timeout=600)
    if r.returncode != 0:
        raise RuntimeError(f"Clone failed for {github_url}: {r.stderr}")
    return target


def compute_pre_bug(repo: Path, buggy_commit: str) -> tuple[str, str, str]:
    """Returns (bug_date_iso, cutoff_date, pre_bug_sha). Raises if any step fails."""
    # 1. Get bug commit date
    r = run(["git", "show", "-s", "--format=%ci", buggy_commit], cwd=repo)
    if r.returncode != 0:
        # Fetch the buggy commit explicitly (BugsInPy SHAs aren't always on default branch)
        run(["git", "fetch", "origin", buggy_commit], cwd=repo, check=False)
        r = run(["git", "show", "-s", "--format=%ci", buggy_commit], cwd=repo)
        if r.returncode != 0:
            raise RuntimeError(f"bug_commit_missing: {buggy_commit}")
    bug_date_iso = r.stdout.strip()

    # 2. Compute cutoff = bug_date - 4 weeks
    bug_dt = datetime.strptime(bug_date_iso[:10], "%Y-%m-%d")
    cutoff_dt = bug_dt - timedelta(weeks=CUTOFF_WEEKS)
    cutoff_str = cutoff_dt.strftime("%Y-%m-%d")

    # 3. PRE_BUG = last commit before cutoff (reachable from buggy_commit's history)
    r = run(["git", "rev-list", "-n", "1", f"--before={cutoff_str}", buggy_commit], cwd=repo)
    if r.returncode != 0 or not r.stdout.strip():
        raise RuntimeError(f"shallow_history: no commit before {cutoff_str}")
    pre_bug = r.stdout.strip()
    return bug_date_iso, cutoff_str, pre_bug


def checkout_pre_bug(repo: Path, pre_bug: str):
    r = run(["git", "checkout", "-q", pre_bug], cwd=repo)
    if r.returncode != 0:
        raise RuntimeError(f"checkout PRE_BUG failed: {r.stderr}")


def file_exists_at_head(repo: Path, file_path: str) -> bool:
    return (repo / file_path).is_file()


def find_rank(results: list, target_file: str) -> int | None:
    """1-based rank of target_file in sorted results. None if not in list."""
    for i, r in enumerate(results, start=1):
        if r["file"] == target_file:
            return i
    return None


def parse_modularity(text: str) -> float | None:
    m = re.search(r'Q\s*=\s*([0-9.]+)', text)
    if m:
        return float(m.group(1))
    return None


def random_baseline(bug_id: str, total_files: int) -> int:
    """Reproducible random rank in [1, total_files] seeded by bug_id."""
    rng = random.Random(hash(bug_id) & 0xFFFFFFFF)
    return rng.randint(1, max(total_files, 1))


def process_case(case: dict, panel: str) -> dict:
    bug_id = case["bug_id"]
    project = case["project"]
    print(f"\n=== {bug_id} ({case['bucket']}, {panel}) ===")

    out = dict(case)
    out["panel"] = panel
    out["status"] = "pending"

    try:
        repo = clone_repo(case["github_url"], project)
        bug_date, cutoff, pre_bug = compute_pre_bug(repo, case["buggy_commit"])
        out["bug_date"] = bug_date
        out["cutoff_date"] = cutoff
        out["pre_bug_commit"] = pre_bug
        print(f"  bug_date={bug_date[:10]}  cutoff={cutoff}  pre_bug={pre_bug[:8]}")

        checkout_pre_bug(repo, pre_bug)

        if not file_exists_at_head(repo, case["change_file"]):
            out["status"] = "skip"
            out["skip_reason"] = "file_missing_at_pre"
            print(f"  SKIP: {case['change_file']} not found at PRE_BUG")
            return out

        # forge.predict_carmack direct (workaround 1+2)
        results_carmack = forge.predict_carmack(repo, weeks=999)
        if not results_carmack:
            out["status"] = "skip"
            out["skip_reason"] = "forge_crashed"
            return out

        out["total_files"] = len(results_carmack)
        rank_carmack = find_rank(results_carmack, case["change_file"])
        out["rank_carmack"] = rank_carmack
        print(f"  carmack: rank={rank_carmack} / {out['total_files']}")

        # forge --modularity (CLI, parse Q)
        r = run([FORGE_BIN, "--modularity", "."], cwd=repo, timeout=120)
        out["q_modularity"] = parse_modularity(r.stdout)
        print(f"  modularity Q = {out['q_modularity']}")

        # forge.predict_defects direct (churn-only baseline)
        # We need rank, so call predict_defects internals or recompute simpler
        # predict_defects only prints; we replicate a churn-only ranking here from carmack data
        # results already have churn signal; sort by churn desc to mimic --predict
        churn_sorted = sorted(results_carmack, key=lambda r: r.get("churn", 0), reverse=True)
        rank_predict = find_rank(churn_sorted, case["change_file"])
        out["rank_predict"] = rank_predict
        print(f"  predict (churn-only): rank={rank_predict} / {len(churn_sorted)}")

        # Random baseline
        out["random_baseline_rank"] = random_baseline(bug_id, out["total_files"])

        # Indicators
        out["norm_rank"] = rank_carmack / out["total_files"] if rank_carmack else None
        out["reciprocal"] = 1.0 / rank_carmack if rank_carmack else 0.0
        out["dcg_at_10"] = (1.0 / math.log2(rank_carmack + 1)) if (rank_carmack and rank_carmack <= 10) else 0.0
        for k in (3, 5, 10, 30):
            out[f"in_top_{k}"] = bool(rank_carmack and rank_carmack <= k)

        out["status"] = "ok"

    except Exception as e:
        out["status"] = "error"
        out["error"] = str(e)
        print(f"  ERROR: {e}")

    return out


def main():
    train = json.loads((ROOT / "panel_train_seed42.json").read_text())
    print(f"Phase A — TRAIN panel: {len(train)} cases\n")

    results_file = ROOT / "results_train.jsonl"
    # Load existing results to resume idempotently
    done_ids = set()
    if results_file.exists():
        for line in results_file.read_text().splitlines():
            if line.strip():
                done_ids.add(json.loads(line)["bug_id"])
        print(f"Already done: {sorted(done_ids)}\n")

    with results_file.open("a") as f:
        for case in train:
            if case["bug_id"] in done_ids:
                print(f"SKIP (already done): {case['bug_id']}")
                continue
            result = process_case(case, panel="train")
            f.write(json.dumps(result) + "\n")
            f.flush()
            print(f"  appended to {results_file.name}")

    print(f"\n=== ALL TRAIN CASES PROCESSED ===")
    print(f"Output: {results_file}")


if __name__ == "__main__":
    main()
