#!/usr/bin/env python3
"""Phase 0.3 — Stratified panel sampling from BugsInPy.

Outputs :
- panel_train_seed42.json : 3+3+3 cases with seed=42
- panel_holdout_seed43.json : 3+3+3 cases with seed=43, disjoint from train
- excluded_repos.md : projects excluded from population with reason

Buckets by Python LOC estimate (bytes / 35):
- small : 1k-5k LOC
- medium : 5k-30k LOC
- large : 30k-200k LOC

Eligibility E1-E6 already pre-verified via gh api (see eligibility_check.txt).
"""
import json
import random
import re
from pathlib import Path

BUGSINPY = Path("/home/sky/forge-case-studies/clones/BugsInPy")

# Pre-verified eligibility (E1: Python>=80%, E5: OSS license, E6: not archived/fork)
# Bytes from gh api repos/<repo>/languages, LOC estimate = bytes/35
ELIGIBLE_PROJECTS = {
    "ansible":      {"github_url": "https://github.com/ansible/ansible",       "py_bytes":  9646387, "loc_est": 275611},
    "black":        {"github_url": "https://github.com/psf/black",             "py_bytes":  5356097, "loc_est": 153032},
    "cookiecutter": {"github_url": "https://github.com/cookiecutter/cookiecutter", "py_bytes":  318259, "loc_est":   9093},
    "fastapi":      {"github_url": "https://github.com/tiangolo/fastapi",      "py_bytes":  3788817, "loc_est": 108252},
    "httpie":       {"github_url": "https://github.com/jakubroztocil/httpie",  "py_bytes":   573376, "loc_est":  16382},
    "keras":        {"github_url": "https://github.com/keras-team/keras",      "py_bytes": 11161843, "loc_est": 318910},
    "luigi":        {"github_url": "https://github.com/spotify/luigi",         "py_bytes":  2181912, "loc_est":  62340},
    "pandas":       {"github_url": "https://github.com/pandas-dev/pandas",     "py_bytes": 22370842, "loc_est": 639167},
    "PySnooper":    {"github_url": "https://github.com/cool-RR/PySnooper",     "py_bytes":   208272, "loc_est":   5950},
    "scrapy":       {"github_url": "https://github.com/scrapy/scrapy",         "py_bytes":  2659831, "loc_est":  75995},
    "thefuck":      {"github_url": "https://github.com/nvbn/thefuck",          "py_bytes":   543910, "loc_est":  15540},
    "tornado":      {"github_url": "https://github.com/tornadoweb/tornado",    "py_bytes":  1633657, "loc_est":  46676},
    "youtube-dl":   {"github_url": "https://github.com/ytdl-org/youtube-dl",   "py_bytes":  6432205, "loc_est": 183777},
}

EXCLUDED_PROJECTS = {
    "matplotlib": "E5 fail: license=null on gh api (custom PSF-style license non auto-detected)",
    "sanic":      "E1 fail: Python 68.4% < 80% threshold",
    "spaCy":      "E1 fail: Python 54.1% < 80% threshold",
    "tqdm":       "E5 fail: license=NOASSERTION on gh api",
}

# Bucket definitions (Sky-spec, frozen)
def bucket_of(loc):
    if 1000 <= loc <= 5000:
        return "small"
    elif 5000 < loc <= 30000:
        return "medium"
    elif 30000 < loc <= 200000:
        return "large"
    else:
        return "out_of_range"


def parse_change_file(bug_dir: Path) -> str | None:
    """Extract the first .py source file modified in bug_patch.txt (not test files)."""
    patch_file = bug_dir / "bug_patch.txt"
    if not patch_file.exists():
        return None
    text = patch_file.read_text(errors="ignore")
    # Look for `diff --git a/PATH b/PATH` then filter out test files
    diffs = re.findall(r'^diff --git a/(\S+)', text, re.MULTILINE)
    for path in diffs:
        if not path.endswith(".py"):
            continue
        # Skip test files for change_file (they are tracked separately as test_file)
        basename = path.split("/")[-1]
        if basename.startswith("test_") or basename.endswith("_test.py") or "/tests/" in path or "/test/" in path:
            continue
        return path
    # Fallback: if all diffs are tests, return the first .py
    for path in diffs:
        if path.endswith(".py"):
            return path
    return None


def parse_bug_info(info_file: Path) -> dict:
    text = info_file.read_text()
    out = {}
    for line in text.splitlines():
        m = re.match(r'^(\w+)="([^"]*)"$', line.strip())
        if m:
            out[m.group(1)] = m.group(2)
    return out


def collect_all_bugs():
    """Walk BugsInPy/projects/<eligible>/bugs/N/ and return list of bug dicts."""
    all_bugs = []
    for proj_name, meta in ELIGIBLE_PROJECTS.items():
        bucket = bucket_of(meta["loc_est"])
        if bucket == "out_of_range":
            continue
        bugs_dir = BUGSINPY / "projects" / proj_name / "bugs"
        if not bugs_dir.exists():
            continue
        for bug_dir in sorted(bugs_dir.iterdir(), key=lambda p: int(p.name) if p.name.isdigit() else 999):
            if not bug_dir.is_dir():
                continue
            info_file = bug_dir / "bug.info"
            if not info_file.exists():
                continue
            info = parse_bug_info(info_file)
            change_file = parse_change_file(bug_dir)
            if not change_file:
                continue
            all_bugs.append({
                "project": proj_name,
                "bug_id": f"{proj_name}-{bug_dir.name}",
                "github_url": meta["github_url"],
                "bucket": bucket,
                "py_bytes": meta["py_bytes"],
                "loc_est": meta["loc_est"],
                "buggy_commit": info.get("buggy_commit_id", ""),
                "fixed_commit": info.get("fixed_commit_id", ""),
                "test_file": info.get("test_file", ""),
                "change_file": change_file,
                "python_version": info.get("python_version", ""),
            })
    return all_bugs


def stratified_sample(bugs, seed, n_per_bucket=3, exclude_ids=None):
    """Return n_per_bucket bugs from each bucket using random.seed(seed)."""
    exclude_ids = exclude_ids or set()
    by_bucket = {"small": [], "medium": [], "large": []}
    for b in bugs:
        if b["bug_id"] in exclude_ids:
            continue
        if b["bucket"] in by_bucket:
            by_bucket[b["bucket"]].append(b)

    rng = random.Random(seed)
    sampled = []
    for bucket in ["small", "medium", "large"]:
        eligible = by_bucket[bucket]
        if len(eligible) < n_per_bucket:
            print(f"WARNING: bucket={bucket} has only {len(eligible)} eligible (needed {n_per_bucket}). Will document in friction.")
            # Take all available, document shortage
            sampled.extend(eligible)
        else:
            chunk = rng.sample(eligible, n_per_bucket)
            sampled.extend(chunk)
    return sampled


def main():
    bugs = collect_all_bugs()
    print(f"Total eligible bugs in population: {len(bugs)}")

    by_bucket_count = {}
    for b in bugs:
        by_bucket_count[b["bucket"]] = by_bucket_count.get(b["bucket"], 0) + 1
    print("By bucket:")
    for bk, n in sorted(by_bucket_count.items()):
        print(f"  {bk}: {n} bugs")

    # Train seed=42
    train = stratified_sample(bugs, seed=42, n_per_bucket=3)
    train_ids = {b["bug_id"] for b in train}

    # Hold-out seed=43, disjoint from train
    holdout = stratified_sample(bugs, seed=43, n_per_bucket=3, exclude_ids=train_ids)
    holdout_ids = {b["bug_id"] for b in holdout}

    # Verify disjoint
    assert train_ids.isdisjoint(holdout_ids), "TRAIN and HOLDOUT must be disjoint"

    # Outputs
    Path("panel_train_seed42.json").write_text(json.dumps(train, indent=2))
    Path("panel_holdout_seed43.json").write_text(json.dumps(holdout, indent=2))

    print(f"\nTRAIN ({len(train)} cases):")
    for b in train:
        print(f"  [{b['bucket']:6}] {b['bug_id']:20} change_file={b['change_file']}")

    print(f"\nHOLDOUT ({len(holdout)} cases):")
    for b in holdout:
        print(f"  [{b['bucket']:6}] {b['bug_id']:20} change_file={b['change_file']}")

    print(f"\nIntersect verification: train ∩ holdout = {train_ids & holdout_ids} (must be empty)")

    # Domain diversity check (Phase 0.4)
    DOMAINS = {
        "ansible": "DevOps", "luigi": "DevOps", "cookiecutter": "DevOps", "scrapy": "DevOps",
        "fastapi": "Web", "tornado": "Web", "sanic": "Web",
        "httpie": "CLI", "thefuck": "CLI", "tqdm": "CLI", "youtube-dl": "CLI",
        "pandas": "Data/ML", "keras": "Data/ML", "matplotlib": "Data/ML", "spaCy": "Data/ML",
        "PySnooper": "Lib/util", "black": "Lib/util",
    }
    train_domains = {DOMAINS.get(b["project"], "?") for b in train}
    holdout_domains = {DOMAINS.get(b["project"], "?") for b in holdout}
    print(f"\nTRAIN domains: {sorted(train_domains)} (count={len(train_domains)}, threshold ≥3)")
    print(f"HOLDOUT domains: {sorted(holdout_domains)} (count={len(holdout_domains)}, threshold ≥3)")


if __name__ == "__main__":
    main()
