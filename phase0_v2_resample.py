#!/usr/bin/env python3
"""Phase 0 v2 step 3 — Re-tirage panel with fillable small bucket.

Per sky-master GO Q3: bucket small fillable from 6 eligible candidates.
Constraint applied to avoid luigi×3 single-project bias: ONE bug per project per bucket.

For each bucket (small, medium, large):
  - List eligible projects (BugsInPy + small fallback)
  - Train: random.sample(eligible_projects, 3, seed=42) -> 3 distinct projects
  - Hold-out: random.sample(remaining, 3, seed=43)     -> 3 distinct projects (disjoint train)
  - Per project, pick 1 bug:
      - BugsInPy: random.choice(bugs_in_project, seed=hash(project) ^ 42)
      - Non-BugsInPy: identify 1 fix commit + parent + change_file via git show

Output: panel_train_v2.json, panel_holdout_v2.json
"""
import csv
import json
import random
import re
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path('/home/sky/forge-case-studies')
BUGSINPY = ROOT / 'clones' / 'BugsInPy'
CLONES_TMP = ROOT / 'clones_tmp_v2'

# 6 small eligible from phase0_v2_small_eligible.csv
SMALL_ELIGIBLE = [
    {'full_name': 'sherlock-project/sherlock', 'loc_est': 2325, 'bucket': 'small'},
    {'full_name': 'lm-sys/RouteLLM',          'loc_est': 2646, 'bucket': 'small'},
    {'full_name': 'pudo/dataset',              'loc_est': 2351, 'bucket': 'small'},
    {'full_name': 'MechanicalSoup/MechanicalSoup', 'loc_est': 3473, 'bucket': 'small'},
    {'full_name': 'blocklistproject/Lists',    'loc_est': 3656, 'bucket': 'small'},
    {'full_name': 'Bing-su/adetailer',         'loc_est': 3823, 'bucket': 'small'},
]

# BugsInPy eligible projets (from cycle 11 v1, confirmed)
BUGSINPY_ELIGIBLE = {
    'medium': ['cookiecutter', 'httpie', 'PySnooper', 'thefuck'],
    'large':  ['ansible', 'black', 'fastapi', 'luigi', 'scrapy', 'tornado', 'youtube-dl'],
}

BUGSINPY_GITHUB_URLS = {
    'cookiecutter': 'https://github.com/cookiecutter/cookiecutter',
    'httpie':       'https://github.com/jakubroztocil/httpie',
    'PySnooper':    'https://github.com/cool-RR/PySnooper',
    'thefuck':      'https://github.com/nvbn/thefuck',
    'ansible':      'https://github.com/ansible/ansible',
    'black':        'https://github.com/psf/black',
    'fastapi':      'https://github.com/tiangolo/fastapi',
    'luigi':        'https://github.com/spotify/luigi',
    'scrapy':       'https://github.com/scrapy/scrapy',
    'tornado':      'https://github.com/tornadoweb/tornado',
    'youtube-dl':   'https://github.com/ytdl-org/youtube-dl',
}


def run(cmd, cwd=None, timeout=60):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)


def parse_bug_info(info_path: Path) -> dict:
    out = {}
    for line in info_path.read_text().splitlines():
        m = re.match(r'^(\w+)="([^"]*)"$', line.strip())
        if m:
            out[m.group(1)] = m.group(2)
    return out


def parse_change_file(bug_dir: Path) -> str | None:
    patch_file = bug_dir / 'bug_patch.txt'
    if not patch_file.exists():
        return None
    text = patch_file.read_text(errors='ignore')
    diffs = re.findall(r'^diff --git a/(\S+)', text, re.MULTILINE)
    for path in diffs:
        if not path.endswith('.py'):
            continue
        basename = path.split('/')[-1]
        if basename.startswith('test_') or basename.endswith('_test.py') or '/tests/' in path or '/test/' in path:
            continue
        return path
    for path in diffs:
        if path.endswith('.py'):
            return path
    return None


def list_bugsinpy_bugs(project: str) -> list[dict]:
    bugs_dir = BUGSINPY / 'projects' / project / 'bugs'
    if not bugs_dir.exists():
        return []
    out = []
    for bug_dir in sorted(bugs_dir.iterdir(), key=lambda p: int(p.name) if p.name.isdigit() else 999):
        if not bug_dir.is_dir():
            continue
        info_file = bug_dir / 'bug.info'
        if not info_file.exists():
            continue
        info = parse_bug_info(info_file)
        change_file = parse_change_file(bug_dir)
        if not change_file:
            continue
        out.append({
            'project': project,
            'bug_id': f'{project}-{bug_dir.name}',
            'github_url': BUGSINPY_GITHUB_URLS[project],
            'buggy_commit': info.get('buggy_commit_id', ''),
            'fixed_commit': info.get('fixed_commit_id', ''),
            'test_file': info.get('test_file', ''),
            'change_file': change_file,
            'python_version': info.get('python_version', ''),
            'source': 'BugsInPy',
        })
    return out


def find_small_bug(full_name: str, repo: Path, seed: int) -> dict | None:
    """For non-BugsInPy small candidate, find 1 fix commit + change_file via diff."""
    rng = random.Random(seed)
    r = run(['git', 'log', '--since=2 years ago', '--grep=fix\\|bug\\|regression',
             '--pretty=format:%H %s', '-50'], cwd=repo, timeout=60)
    if r.returncode != 0 or not r.stdout.strip():
        return None
    commits = [line.split(' ', 1) for line in r.stdout.strip().splitlines() if line.strip()]
    rng.shuffle(commits)
    for sha, msg in commits[:30]:
        # Get .py files modified in this commit (excluding tests)
        sr = run(['git', 'show', '--pretty=format:', '--name-only', sha], cwd=repo, timeout=30)
        if sr.returncode != 0:
            continue
        py_files = [f.strip() for f in sr.stdout.splitlines() if f.strip().endswith('.py')]
        non_test = [f for f in py_files if not (
            f.startswith('test_') or f.endswith('_test.py')
            or '/tests/' in f or '/test/' in f
            or f.startswith('tests/') or f.startswith('test/')
        )]
        if non_test:
            change_file = non_test[0]
        elif py_files:
            change_file = py_files[0]
        else:
            continue
        # buggy_commit = parent of fix
        pr = run(['git', 'rev-parse', f'{sha}^'], cwd=repo, timeout=10)
        if pr.returncode != 0:
            continue
        buggy = pr.stdout.strip()
        return {
            'project': full_name.split('/')[-1].replace('.', '_'),
            'bug_id': f'{full_name.split("/")[-1].replace(".", "_")}-{sha[:7]}',
            'github_url': f'https://github.com/{full_name}',
            'buggy_commit': buggy,
            'fixed_commit': sha,
            'test_file': '',
            'change_file': change_file,
            'python_version': '',
            'source': 'gh_search_fallback',
            'fix_msg': msg.strip()[:80],
        }
    return None


def sample_panel(seed: int, exclude_small_projects: list = None) -> list:
    """Sample 3 distinct projects per bucket for one panel.

    Constraint: 1 bug per project per panel (no luigi×3 bias).
    Project overlap between TRAIN and HOLDOUT allowed for medium/large
    (different bug_id via different seeds, panels remain disjoint at bug level).
    For small (only 6 projects total): partition strictly disjoint via exclude.
    """
    exclude_small_projects = exclude_small_projects or []
    panel = []

    # === BUCKET small ===
    rng = random.Random(seed)
    small_eligible = [c['full_name'] for c in SMALL_ELIGIBLE
                      if c['full_name'] not in exclude_small_projects]
    small_sample = rng.sample(small_eligible, min(3, len(small_eligible)))
    print(f"  small projects sampled (seed={seed}): {small_sample}")
    for full_name in small_sample:
        short = full_name.split('/')[-1].replace('.', '_')
        repo = CLONES_TMP / short
        if not (repo / '.git').exists():
            print(f"    {short}: clone missing — fetching...")
            r = run(['git', 'clone', '--quiet', '--filter=blob:none',
                     f'https://github.com/{full_name}.git', str(repo)], timeout=180)
            if r.returncode != 0:
                print(f"    {short}: clone FAILED")
                continue
        bug = find_small_bug(full_name, repo, seed=hash(full_name) ^ seed)
        if bug:
            bug['bucket'] = 'small'
            panel.append(bug)
            print(f"    {bug['bug_id']:35} change_file={bug['change_file']}")

    # === BUCKET medium ===
    rng = random.Random(seed + 100)  # different seed so different projects
    medium_projs = list(BUGSINPY_ELIGIBLE['medium'])  # all 4, project overlap allowed btwn panels
    medium_sample = rng.sample(medium_projs, min(3, len(medium_projs)))
    print(f"  medium projects sampled (seed={seed+100}): {medium_sample}")
    for proj in medium_sample:
        bugs = list_bugsinpy_bugs(proj)
        if not bugs:
            continue
        rng2 = random.Random(hash(proj) ^ seed)
        bug = rng2.choice(bugs)
        bug['bucket'] = 'medium'
        panel.append(bug)
        print(f"    {bug['bug_id']:35} change_file={bug['change_file']}")

    # === BUCKET large ===
    rng = random.Random(seed + 200)
    large_projs = list(BUGSINPY_ELIGIBLE['large'])  # all 7, project overlap allowed btwn panels
    large_sample = rng.sample(large_projs, min(3, len(large_projs)))
    print(f"  large projects sampled (seed={seed+200}): {large_sample}")
    for proj in large_sample:
        bugs = list_bugsinpy_bugs(proj)
        if not bugs:
            continue
        rng2 = random.Random(hash(proj) ^ seed)
        bug = rng2.choice(bugs)
        bug['bucket'] = 'large'
        panel.append(bug)
        print(f"    {bug['bug_id']:35} change_file={bug['change_file']}")

    return panel


def main():
    print("=== Phase 0 v2 — Sampling TRAIN (seed=42) ===")
    train = sample_panel(seed=42)
    print(f"\nTRAIN total: {len(train)} cases\n")

    # For HOLDOUT, exclude small projects already in TRAIN (only 6 small available)
    # medium/large allow project overlap between panels (different bugs via seeds)
    train_small_projects = [c['github_url'].replace('https://github.com/', '') for c in train if c['bucket'] == 'small']
    print(f"=== Phase 0 v2 — Sampling HOLDOUT (seed=43, small projects disjoint from TRAIN) ===")
    print(f"  Train small projects excluded: {train_small_projects}")
    holdout = sample_panel(seed=43, exclude_small_projects=train_small_projects)
    print(f"\nHOLDOUT total: {len(holdout)} cases\n")

    # Verify disjoint at bug_id level (critical) and small-project disjoint
    train_ids = {b['bug_id'] for b in train}
    holdout_ids = {b['bug_id'] for b in holdout}
    train_small_projs = {b['project'] for b in train if b['bucket'] == 'small'}
    holdout_small_projs = {b['project'] for b in holdout if b['bucket'] == 'small'}
    print(f"intersect bug_ids: {train_ids & holdout_ids}")
    print(f"intersect SMALL projects (must be empty): {train_small_projs & holdout_small_projs}")
    assert not (train_ids & holdout_ids), "Panels must be disjoint at bug_id level"
    assert not (train_small_projs & holdout_small_projs), "Small projects must be disjoint train/holdout (only 6 available)"

    (ROOT / 'panel_train_v2.json').write_text(json.dumps(train, indent=2))
    (ROOT / 'panel_holdout_v2.json').write_text(json.dumps(holdout, indent=2))

    # Print summary
    print(f"\n=== TRAIN ({len(train)} cases) ===")
    for b in train:
        print(f"  [{b['bucket']:6}] {b['bug_id']:40} {b['source']:20} change_file={b['change_file']}")

    print(f"\n=== HOLDOUT ({len(holdout)} cases) ===")
    for b in holdout:
        print(f"  [{b['bucket']:6}] {b['bug_id']:40} {b['source']:20} change_file={b['change_file']}")

    print(f"\nSaved panel_train_v2.json + panel_holdout_v2.json")


if __name__ == "__main__":
    main()
