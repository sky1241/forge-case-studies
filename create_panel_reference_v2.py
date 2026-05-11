#!/usr/bin/env python3
"""Create panel_reference.json v2 — anti-bias diversification projects/files.

Constraints:
- Max 2 cases per project (relaxed from "max 1" because BugsInPy only has 13 projects)
- Max 1 case per change_file (no doubled files)
- Stratification 5+5+5+5: history-rich + medium-history + cold-start + mixed
- Seed=999 (same seed but with diversity constraints)
"""
import csv
import json
import random
from collections import Counter
from pathlib import Path

ROOT = Path('/home/sky/forge-case-studies')

URLS = {
    'cookiecutter': 'https://github.com/cookiecutter/cookiecutter',
    'httpie': 'https://github.com/jakubroztocil/httpie',
    'PySnooper': 'https://github.com/cool-RR/PySnooper',
    'thefuck': 'https://github.com/nvbn/thefuck',
    'ansible': 'https://github.com/ansible/ansible',
    'black': 'https://github.com/psf/black',
    'fastapi': 'https://github.com/tiangolo/fastapi',
    'luigi': 'https://github.com/spotify/luigi',
    'scrapy': 'https://github.com/scrapy/scrapy',
    'tornado': 'https://github.com/tornadoweb/tornado',
    'youtube-dl': 'https://github.com/ytdl-org/youtube-dl',
}

MAX_PER_PROJECT = 2  # relaxed because BugsInPy has only 13 eligible projects
MAX_PER_CHANGE_FILE = 1

pool = []
with open(ROOT / 'phase0_v4_e7_eligible.csv') as f:
    for r in csv.DictReader(f):
        if r['skip_reason'] in ('shallow_history', 'clone_failed', 'bug_commit_missing'):
            continue
        pool.append({
            'project': r['project'],
            'bug_id': r['bug_id'],
            'bucket': r['bucket'],
            'change_file': r['change_file'],
            'github_url': URLS.get(r['project'], f"https://github.com/{r['project']}"),
            'fix_count': int(r['fix_count']),
        })

print(f"Pool: {len(pool)} bugs")

history = [b for b in pool if b['fix_count'] >= 3]
medium = [b for b in pool if 1 <= b['fix_count'] <= 2]
cold = [b for b in pool if b['fix_count'] == 0]
print(f"  history (≥3): {len(history)}  medium (1-2): {len(medium)}  cold (0): {len(cold)}")

# Project distribution check
def project_dist(lst, label):
    c = Counter(b['project'] for b in lst)
    print(f"  {label} project dist: {dict(c)}")

project_dist(history, 'history')
project_dist(medium, 'medium')
project_dist(cold, 'cold')

rng = random.Random(999)
selected = []
proj_counts: dict[str, int] = {}
files_used: set[str] = set()


def sample_with_constraints(candidates, n_target, label):
    """Sample n_target from candidates while respecting MAX_PER_PROJECT + MAX_PER_CHANGE_FILE."""
    cands = list(candidates)
    rng.shuffle(cands)
    out = []
    for c in cands:
        if len(out) >= n_target:
            break
        if proj_counts.get(c['project'], 0) >= MAX_PER_PROJECT:
            continue
        if c['change_file'] in files_used:
            continue
        c['reference_subset'] = label
        out.append(c)
        proj_counts[c['project']] = proj_counts.get(c['project'], 0) + 1
        files_used.add(c['change_file'])
        selected.append(c)
    return out


ref_history = sample_with_constraints(history, 5, 'history-rich')
ref_medium = sample_with_constraints(medium, 5, 'medium-history')
ref_cold = sample_with_constraints(cold, 5, 'cold-start')

# Mixed: sample from all not-yet-selected respecting constraints
mixed_pool = [b for b in pool if b['bug_id'] not in {x['bug_id'] for x in selected}]
ref_mixed = sample_with_constraints(mixed_pool, 5, 'mixed')

print(f"\n=== Panel reference v2 N={len(selected)} ===")
print(f"\nProject distribution (final):")
final_dist = Counter(b['project'] for b in selected)
for p, n in sorted(final_dist.items(), key=lambda x: -x[1]):
    print(f"  {p:<15}: {n} cases")

print(f"\nChange files distribution: {len(files_used)} unique files (target {len(selected)} for 0 duplicates)")
assert len(files_used) == len(selected), f"DUPLICATE FILES! {len(files_used)} unique vs {len(selected)} cases"
print(f"  ✓ No file duplicates")

print(f"\nDetail:")
for sub in ['history-rich', 'medium-history', 'cold-start', 'mixed']:
    cases = [b for b in selected if b['reference_subset'] == sub]
    print(f"  {sub} ({len(cases)}):")
    for b in cases:
        print(f"    {b['bug_id']:<22} bucket={b['bucket']:<8} fix_count={b['fix_count']:<3} cf={b['change_file']}")

(ROOT / 'panel_reference.json').write_text(json.dumps(selected, indent=2))
print(f"\nSaved panel_reference.json v2 ({len(selected)} cases) — committed permanent, seed=999, max 2/project")
