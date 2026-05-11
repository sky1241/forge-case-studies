#!/usr/bin/env python3
"""Phase 0 v4 — Sample panel seeds 46/47 from E7-eligible pool.

Pool: 169 bugs E1-E7 (14 medium + 155 large). Small bucket impossible
even with E7 filter on BugsInPy (small fallback non-BugsInPy not checked
because change_file is randomly drawn, no pre-defined bug to filter).

Target: 25 train + 25 holdout = 50 cases.
Stratification: 0 small + 7 medium + 18 large per panel.
Multi-bug per project allowed (only 4 medium projects available).
Train/holdout disjoint at bug_id level.
"""
import json
import random
from pathlib import Path

ROOT = Path('/home/sky/forge-case-studies')

pool = json.loads((ROOT / 'phase0_v4_e7_pool.json').read_text())
medium = [b for b in pool if b['bucket'] == 'medium']
large = [b for b in pool if b['bucket'] == 'large']

print(f"Pool E7-eligible: {len(pool)} bugs (medium={len(medium)}, large={len(large)})")
print()

# === TRAIN seed=46 ===
rng_m = random.Random(46)
rng_l = random.Random(46 + 100)

medium_train = rng_m.sample(medium, 7)
large_train = rng_l.sample(large, 18)
train = medium_train + large_train

train_ids = {b['bug_id'] for b in train}

# === HOLDOUT seed=47, disjoint from train ===
rng_m = random.Random(47)
rng_l = random.Random(47 + 100)

medium_pool_h = [b for b in medium if b['bug_id'] not in train_ids]
large_pool_h = [b for b in large if b['bug_id'] not in train_ids]
medium_holdout = rng_m.sample(medium_pool_h, min(7, len(medium_pool_h)))
large_holdout = rng_l.sample(large_pool_h, min(18, len(large_pool_h)))
holdout = medium_holdout + large_holdout

holdout_ids = {b['bug_id'] for b in holdout}
assert not (train_ids & holdout_ids), "Panels must be disjoint at bug_id"

print(f"=== TRAIN seed=46 ===")
print(f"  medium: {len(medium_train)} cases")
for b in medium_train: print(f"    {b['bug_id']:30} change_file={b['change_file']}")
print(f"  large: {len(large_train)} cases")
for b in large_train: print(f"    {b['bug_id']:30} change_file={b['change_file']}")
print(f"  TOTAL TRAIN: {len(train)}")
print()
print(f"=== HOLDOUT seed=47 (disjoint) ===")
print(f"  medium: {len(medium_holdout)} cases")
for b in medium_holdout: print(f"    {b['bug_id']:30} change_file={b['change_file']}")
print(f"  large: {len(large_holdout)} cases")
for b in large_holdout: print(f"    {b['bug_id']:30} change_file={b['change_file']}")
print(f"  TOTAL HOLDOUT: {len(holdout)}")
print()
print(f"=== TOTAL N={len(train)+len(holdout)} ===")

# Save
(ROOT / 'panel_train_v4.json').write_text(json.dumps(train, indent=2))
(ROOT / 'panel_holdout_v4.json').write_text(json.dumps(holdout, indent=2))
print(f"\nSaved panel_train_v4.json + panel_holdout_v4.json")
