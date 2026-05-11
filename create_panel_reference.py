#!/usr/bin/env python3
"""Create panel_reference.json — 20 fixed cases, seed=999, committed permanent.

Used by every future cycle (15-20+) to track regression across iterations
on the SAME bugs. Performance comparison cycle N vs N-1.

Stratification:
- 5 history-rich (bugfixes >= 3 on change_file)
- 5 cold-start (bugfixes 0)
- 5 medium-history (bugfixes 1-2)
- 5 mixed (random from full pool)
"""
import csv
import json
import random
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

# Load full pool from cycle 13 E7 results
pool = []
with open(ROOT / 'phase0_v4_e7_eligible.csv') as f:
    for r in csv.DictReader(f):
        if r['skip_reason'] in ('shallow_history', 'clone_failed', 'bug_commit_missing'):
            continue
        entry = {
            'project': r['project'],
            'bug_id': r['bug_id'],
            'bucket': r['bucket'],
            'change_file': r['change_file'],
            'github_url': URLS.get(r['project'], f"https://github.com/{r['project']}"),
            'fix_count': int(r['fix_count']),
        }
        pool.append(entry)

print(f"Pool: {len(pool)} bugs (cycle 13 E7-checked)")

# Stratify
history_rich = [b for b in pool if b['fix_count'] >= 3]
medium = [b for b in pool if 1 <= b['fix_count'] <= 2]
cold = [b for b in pool if b['fix_count'] == 0]
print(f"  history-rich (≥3): {len(history_rich)}")
print(f"  medium (1-2):     {len(medium)}")
print(f"  cold-start (0):   {len(cold)}")

# Sample with seed=999
rng = random.Random(999)
chosen_ids = set()

def sample_n(pool_, n_target, label):
    eligible = [b for b in pool_ if b['bug_id'] not in chosen_ids]
    n = min(n_target, len(eligible))
    selected = rng.sample(eligible, n)
    for b in selected:
        chosen_ids.add(b['bug_id'])
        b['reference_subset'] = label
    return selected

ref_history = sample_n(history_rich, 5, 'history-rich')
ref_medium = sample_n(medium, 5, 'medium-history')
ref_cold = sample_n(cold, 5, 'cold-start')
ref_mixed = sample_n(pool, 5, 'mixed')

ref_panel = ref_history + ref_medium + ref_cold + ref_mixed
print(f"\nPanel reference N={len(ref_panel)}:")
for sub in ['history-rich', 'medium-history', 'cold-start', 'mixed']:
    cases = [b for b in ref_panel if b['reference_subset'] == sub]
    print(f"  {sub} ({len(cases)}):")
    for b in cases:
        print(f"    {b['bug_id']:<25} bucket={b['bucket']:<8} fix_count={b['fix_count']:<3} cf={b['change_file']}")

(ROOT / 'panel_reference.json').write_text(json.dumps(ref_panel, indent=2))
print(f"\nSaved panel_reference.json ({len(ref_panel)} cases) — committed permanent, seed=999")
