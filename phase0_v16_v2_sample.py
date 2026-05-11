#!/usr/bin/env python3
"""Phase 0 v16 v2 — Sample N=50 cold-start panel, seeds 52/53 split 25/25.

Sample N=50 cold-start cases (E7 fail, bugfixes < 3 on change_file).
Train (seed=52) N=25 + Holdout (seed=53) N=25.

Cycle 16 v1 was interrupted at N=14 (early stop). v2 is the proper run
per sky-master directive : NO EARLY STOPPING. Complete the panel.
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

cold = []
with open(ROOT / 'phase0_v4_e7_eligible.csv') as f:
    for r in csv.DictReader(f):
        if r['skip_reason'] == 'cold_start_blind_e7':
            cold.append({
                'project': r['project'],
                'bug_id': r['bug_id'],
                'bucket': r['bucket'],
                'change_file': r['change_file'],
                'github_url': URLS[r['project']],
                'fix_count': int(r['fix_count']),
            })

print(f"Cold-start pool (cycle 13 E7 fail bugfixes<3): {len(cold)} cases")
# Total pool 60 → 50 sampled (25 train + 25 holdout)

rng = random.Random(52)
rng.shuffle(cold)
train = cold[:25]
holdout = cold[25:50]
print(f"TRAIN seed=52: {len(train)} cases")
print(f"HOLDOUT seed=53: {len(holdout)} cases (disjoint)")

(ROOT / 'panel_train_seed52.json').write_text(json.dumps(train, indent=2))
(ROOT / 'panel_holdout_seed53.json').write_text(json.dumps(holdout, indent=2))
print(f"\nSaved panel files. N=50 total.")
