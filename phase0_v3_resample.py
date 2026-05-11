#!/usr/bin/env python3
"""Phase 0 v3 — Tirage panel N=50 (25 train + 25 holdout) seeds 44/45.

Stratification:
  small  : 3 train + 3 holdout (max 6 eligible from cycle 11 v2)
  medium : 11 train + 11 holdout (44 BugsInPy bugs, 4 projects, multi-bug/project)
  large  : 11 train + 11 holdout (171 BugsInPy bugs, 7 projects, multi-bug/project)
Total: N=25 train + N=25 holdout = 50 cases.

Bugs disjoint train/holdout at bug_id level.
Small projects strictly disjoint train/holdout (only 6 available).
"""
import json
import random
import re
import subprocess
from pathlib import Path

ROOT = Path('/home/sky/forge-case-studies')
BUGSINPY = ROOT / 'clones' / 'BugsInPy'
CLONES_TMP = ROOT / 'clones_tmp_v2'

SMALL_ELIGIBLE = [
    'sherlock-project/sherlock',
    'lm-sys/RouteLLM',
    'pudo/dataset',
    'MechanicalSoup/MechanicalSoup',
    'blocklistproject/Lists',
    'Bing-su/adetailer',
]

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
    patch = bug_dir / 'bug_patch.txt'
    if not patch.exists():
        return None
    text = patch.read_text(errors='ignore')
    diffs = re.findall(r'^diff --git a/(\S+)', text, re.MULTILINE)
    for p in diffs:
        if not p.endswith('.py'):
            continue
        base = p.split('/')[-1]
        if base.startswith('test_') or base.endswith('_test.py') or '/tests/' in p or '/test/' in p:
            continue
        return p
    for p in diffs:
        if p.endswith('.py'):
            return p
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
        cf = parse_change_file(bug_dir)
        if not cf:
            continue
        out.append({
            'project': project, 'bug_id': f'{project}-{bug_dir.name}',
            'github_url': BUGSINPY_GITHUB_URLS[project], 'bucket': '',
            'buggy_commit': info.get('buggy_commit_id', ''),
            'fixed_commit': info.get('fixed_commit_id', ''),
            'test_file': info.get('test_file', ''),
            'change_file': cf,
            'python_version': info.get('python_version', ''),
            'source': 'BugsInPy',
        })
    return out


def find_small_bug(full_name: str, repo: Path, seed: int, exclude_shas: set = None) -> dict | None:
    """For non-BugsInPy small candidate, find 1 fix commit with .py change_file."""
    exclude_shas = exclude_shas or set()
    rng = random.Random(seed)
    r = run(['git', 'log', '--since=2 years ago', '--grep=fix\\|bug\\|regression',
             '--pretty=format:%H %s', '-50'], cwd=repo, timeout=60)
    if r.returncode != 0 or not r.stdout.strip():
        return None
    commits = [line.split(' ', 1) for line in r.stdout.strip().splitlines() if line.strip()]
    rng.shuffle(commits)
    for sha, msg in commits[:30]:
        if sha in exclude_shas:
            continue
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
            cf = non_test[0]
        elif py_files:
            cf = py_files[0]
        else:
            continue
        pr = run(['git', 'rev-parse', f'{sha}^'], cwd=repo, timeout=10)
        if pr.returncode != 0:
            continue
        buggy = pr.stdout.strip()
        return {
            'project': full_name.split('/')[-1].replace('.', '_'),
            'bug_id': f'{full_name.split("/")[-1].replace(".", "_")}-{sha[:7]}',
            'github_url': f'https://github.com/{full_name}',
            'bucket': 'small',
            'buggy_commit': buggy,
            'fixed_commit': sha,
            'test_file': '',
            'change_file': cf,
            'python_version': '',
            'source': 'gh_search_fallback',
            'fix_msg': msg.strip()[:80],
        }
    return None


def sample_panel(seed: int, n_per_bucket: dict, exclude_small: list = None, exclude_bug_ids: set = None) -> list:
    exclude_small = exclude_small or []
    exclude_bug_ids = exclude_bug_ids or set()
    panel = []

    # === SMALL ===
    rng = random.Random(seed)
    small_pool = [c for c in SMALL_ELIGIBLE if c not in exclude_small]
    small_target = min(n_per_bucket['small'], len(small_pool))
    small_sample = rng.sample(small_pool, small_target)
    print(f"\n  SMALL projects (seed={seed}): {small_sample}")
    for full_name in small_sample:
        short = full_name.split('/')[-1].replace('.', '_')
        repo = CLONES_TMP / short
        if not (repo / '.git').exists():
            run(['git', 'clone', '--quiet', '--filter=blob:none',
                 f'https://github.com/{full_name}.git', str(repo)], timeout=180)
        bug = find_small_bug(full_name, repo, seed=hash(full_name) ^ seed)
        if bug and bug['bug_id'] not in exclude_bug_ids:
            panel.append(bug)
            print(f"    {bug['bug_id']:40} cf={bug['change_file']}")
        else:
            print(f"    {full_name:40} FAILED find_small_bug or duplicate")

    # === MEDIUM ===
    medium_pool = []
    for proj in BUGSINPY_ELIGIBLE['medium']:
        medium_pool.extend(list_bugsinpy_bugs(proj))
    medium_pool = [b for b in medium_pool if b['bug_id'] not in exclude_bug_ids]
    rng = random.Random(seed + 100)
    medium_target = min(n_per_bucket['medium'], len(medium_pool))
    medium_sample = rng.sample(medium_pool, medium_target)
    print(f"\n  MEDIUM (seed={seed+100}): tirage {medium_target} sur {len(medium_pool)} bugs eligibles")
    for b in medium_sample:
        b['bucket'] = 'medium'
        panel.append(b)
        print(f"    {b['bug_id']:40} cf={b['change_file']}")

    # === LARGE ===
    large_pool = []
    for proj in BUGSINPY_ELIGIBLE['large']:
        large_pool.extend(list_bugsinpy_bugs(proj))
    large_pool = [b for b in large_pool if b['bug_id'] not in exclude_bug_ids]
    rng = random.Random(seed + 200)
    large_target = min(n_per_bucket['large'], len(large_pool))
    large_sample = rng.sample(large_pool, large_target)
    print(f"\n  LARGE (seed={seed+200}): tirage {large_target} sur {len(large_pool)} bugs eligibles")
    for b in large_sample:
        b['bucket'] = 'large'
        panel.append(b)
        print(f"    {b['bug_id']:40} cf={b['change_file']}")

    return panel


def main():
    targets = {'small': 3, 'medium': 11, 'large': 11}  # 25 cases per panel
    print("=== Phase 0 v3 — Sampling TRAIN (seed=44) ===")
    train = sample_panel(seed=44, n_per_bucket=targets)
    train_ids = {b['bug_id'] for b in train}
    train_small_proj = [b['github_url'].replace('https://github.com/', '') for b in train if b['bucket']=='small']
    print(f"\nTRAIN total: {len(train)} cases")

    print(f"\n=== Phase 0 v3 — Sampling HOLDOUT (seed=45, exclude TRAIN bug_ids + small projects) ===")
    holdout = sample_panel(seed=45, n_per_bucket=targets,
                           exclude_small=train_small_proj, exclude_bug_ids=train_ids)
    holdout_ids = {b['bug_id'] for b in holdout}

    inter = train_ids & holdout_ids
    print(f"\nintersect bug_ids: {inter}")
    assert not inter, "Panels must be disjoint"

    (ROOT / 'panel_train_v3.json').write_text(json.dumps(train, indent=2))
    (ROOT / 'panel_holdout_v3.json').write_text(json.dumps(holdout, indent=2))

    print(f"\n=== SUMMARY ===")
    print(f"TRAIN N={len(train)}: small={sum(1 for b in train if b['bucket']=='small')}, "
          f"medium={sum(1 for b in train if b['bucket']=='medium')}, "
          f"large={sum(1 for b in train if b['bucket']=='large')}")
    print(f"HOLDOUT N={len(holdout)}: small={sum(1 for b in holdout if b['bucket']=='small')}, "
          f"medium={sum(1 for b in holdout if b['bucket']=='medium')}, "
          f"large={sum(1 for b in holdout if b['bucket']=='large')}")
    print(f"\nTotal N={len(train)+len(holdout)} cases")


if __name__ == "__main__":
    main()
