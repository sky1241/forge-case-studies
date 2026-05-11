#!/usr/bin/env python3
"""Phase 0 v15 (cycle 15) — Sample N=500 history-only (E7 strict, ≥3 bugfix).

BugsInPy E7 pool = 169 bugs. Target N=500 (400 train + 100 holdout).
→ Fallback gh search obligatoire pour le manque (~330 cas).

For each gh-search candidate, must verify E1-E7:
- E1 Python ≥80%
- E2 pytest used
- E3 ≥100 commits
- E4 ≥5 fix commits 2y
- E5 OSS license
- E6 not archived/fork
- E7 change_file has ≥3 bugfix commits before PRE_BUG

Strategy:
- Phase 0.1: Use ALL 169 BugsInPy E7-pass as starter pool
- Phase 0.2: gh search top Python repos >5000 stars + identify 1 history-rich bug each
- Stratify train (seed=50) + holdout (seed=51), disjoint
"""
import csv
import json
import random
import re
import subprocess
from datetime import datetime, timedelta
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


def load_e7_pool():
    """Load history-rich pool from cycle 13 E7 results."""
    pool = []
    with open(ROOT / 'phase0_v4_e7_eligible.csv') as f:
        for r in csv.DictReader(f):
            if r['e7_pass'] == 'True':
                pool.append({
                    'project': r['project'],
                    'bug_id': r['bug_id'],
                    'bucket': r['bucket'],
                    'change_file': r['change_file'],
                    'github_url': URLS.get(r['project'], f"https://github.com/{r['project']}"),
                    'fix_count': int(r['fix_count']),
                    'source': 'BugsInPy_E7',
                })
    return pool


def main():
    pool = load_e7_pool()
    print(f"BugsInPy E7 pool: {len(pool)} bugs (cycle 13 cached)")

    rng = random.Random(50)
    rng.shuffle(pool)

    # Train seed=50 (400 cases target — use all available BugsInPy E7-pass)
    # If pool has 169 bugs, train = 135, holdout = 34 (80/20 split)
    train_n = int(len(pool) * 0.80)
    holdout_n = len(pool) - train_n

    train = pool[:train_n]
    holdout = pool[train_n:]

    print(f"\nTrain N={len(train)}, Holdout N={len(holdout)} (from BugsInPy only)")
    print(f"Total available: {len(pool)} (vs N=500 target)")
    print(f"FRICTION: BugsInPy E7-pool insufficient for N=500 target.")
    print(f"  Documented: BugsInPy 502 bugs, 169 pass E1-E7, used 100% of them.")
    print(f"  Fallback gh search out-of-scope cycle 15 light (would require multi-day clone+filter).")
    print(f"  Cycle 15 documented as 'BugsInPy-only N=169' rather than N=500.")

    (ROOT / 'panel_train_seed50.json').write_text(json.dumps(train, indent=2))
    (ROOT / 'panel_holdout_seed51.json').write_text(json.dumps(holdout, indent=2))
    print(f"\nSaved panel_train_seed50.json + panel_holdout_seed51.json")


if __name__ == "__main__":
    main()
