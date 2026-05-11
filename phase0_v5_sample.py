#!/usr/bin/env python3
"""Phase 0 v5 (cycle 14) — Sample N=180 stratified by E7 (cold-start / history-rich).

Source pool: phase0_v4_e7_eligible.csv (233 BugsInPy bugs E1-E6 + E7 check):
- E7 pass (bugfixes >= 3): 169 bugs (history-rich pool)
- E7 fail (bugfixes < 3): 60 bugs (cold-start pool)
- shallow_history: 4 (skip)

Target N=180 (vs brief N=200 — cold-start dispo limit 60 vs 80 desired).
Stratification 80/20 train/holdout split, ratio cold-start/history maintained.

Train (seed=48):  48 cold-start + 96 history = 144
Holdout (seed=49): 12 cold-start + 24 history = 36
Total: 60 cold-start + 120 history = 180

Verify disjoint at bug_id level.
"""
import csv
import json
import random
import re
from pathlib import Path

ROOT = Path('/home/sky/forge-case-studies')
BUGSINPY = ROOT / 'clones' / 'BugsInPy'

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


def load_pool():
    cold = []
    hist = []
    with open(ROOT / 'phase0_v4_e7_eligible.csv') as f:
        for r in csv.DictReader(f):
            entry = {
                'project': r['project'], 'bug_id': r['bug_id'],
                'bucket': r['bucket'], 'change_file': r['change_file'],
                'github_url': URLS.get(r['project'], f"https://github.com/{r['project']}/{r['project']}"),
                'fix_count': int(r['fix_count']),
                'cold_start': r['skip_reason'] == 'cold_start_blind_e7',
            }
            if r['e7_pass'] == 'True':
                hist.append(entry)
            elif r['skip_reason'] == 'cold_start_blind_e7':
                cold.append(entry)
    return cold, hist


def stratified_sample(pool, target_n, seed):
    rng = random.Random(seed)
    if target_n >= len(pool):
        return list(pool)
    return rng.sample(pool, target_n)


def main():
    cold, hist = load_pool()
    print(f"Pool E7: cold-start={len(cold)}, history-rich={len(hist)}")

    # TRAIN seed=48: 48 cold + 96 hist
    train_cold = stratified_sample(cold, 48, seed=48)
    train_hist = stratified_sample(hist, 96, seed=48 + 100)
    train_ids = {b['bug_id'] for b in train_cold + train_hist}

    # HOLDOUT seed=49: 12 cold + 24 hist, disjoint from train
    cold_remain = [b for b in cold if b['bug_id'] not in train_ids]
    hist_remain = [b for b in hist if b['bug_id'] not in train_ids]
    print(f"After train: cold_remain={len(cold_remain)}, hist_remain={len(hist_remain)}")

    holdout_cold = stratified_sample(cold_remain, 12, seed=49)
    holdout_hist = stratified_sample(hist_remain, 24, seed=49 + 100)

    train = train_cold + train_hist
    holdout = holdout_cold + holdout_hist

    # Verify disjoint
    holdout_ids = {b['bug_id'] for b in holdout}
    assert not (train_ids & holdout_ids), "panels must be disjoint at bug_id"

    # Save
    (ROOT / 'panel_train_seed48.json').write_text(json.dumps(train, indent=2))
    (ROOT / 'panel_holdout_seed49.json').write_text(json.dumps(holdout, indent=2))

    print(f"\nTRAIN N={len(train)}: cold={len(train_cold)} + history={len(train_hist)}")
    print(f"HOLDOUT N={len(holdout)}: cold={len(holdout_cold)} + history={len(holdout_hist)}")
    print(f"Total N={len(train) + len(holdout)}")
    print(f"Train projects: {sorted({b['project'] for b in train})}")
    print(f"Holdout projects: {sorted({b['project'] for b in holdout})}")


if __name__ == "__main__":
    main()
