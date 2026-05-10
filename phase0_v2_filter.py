#!/usr/bin/env python3
"""Phase 0 v2 — Exhaust 400+ candidates for bucket small fallback.

Step 1: Filter E5+E6 (OSS license, not archived/fork/disabled) on 400 repos.
Step 2: gh api languages -> Python bytes -> LOC est. (÷35).
Step 3: Keep only LOC ∈ [500, 5000] (extended small range).
Step 4: Save phase0_v2_small_candidates.csv (one row per candidate with verdict).

Output: list of E5+E6 + bucket small candidates ready for E1-E4 deep check.
"""
import csv
import json
import subprocess
from pathlib import Path

ROOT = Path('/home/sky/forge-case-studies')
OSS_OK = {'mit', 'apache-2.0', 'bsd-3-clause', 'bsd-2-clause', 'gpl-3.0', 'gpl-2.0', 'lgpl-3.0', 'lgpl-2.1', 'isc', 'mpl-2.0', 'agpl-3.0', 'unlicense', '0bsd'}

# BugsInPy 17 projets (already in cycle 11 v1)
BUGSINPY_NAMES = {'ansible', 'black', 'cookiecutter', 'fastapi', 'httpie', 'keras', 'luigi',
                  'matplotlib', 'pandas', 'PySnooper', 'sanic', 'scrapy', 'spaCy', 'thefuck',
                  'tornado', 'tqdm', 'youtube-dl'}


def get_python_bytes(owner_repo: str) -> int:
    """gh api repos/X/Y/languages -> Python bytes. Returns 0 on error."""
    try:
        r = subprocess.run(['gh', 'api', f'repos/{owner_repo}/languages'],
                           capture_output=True, text=True, timeout=15)
        if r.returncode == 0 and r.stdout.strip():
            return json.loads(r.stdout).get('Python', 0)
    except Exception:
        pass
    return 0


def main():
    rows = []
    seen = set()

    for batch_file, label in [('/tmp/gh_search_5k.json', 'stars>5000'),
                               ('/tmp/gh_search_1k.json', 'stars:1000-5000')]:
        data = json.load(open(batch_file))
        print(f"\n=== Batch {label}: {len(data)} repos ===")
        for i, r in enumerate(data, 1):
            full_name = r['fullName']
            if full_name in seen:
                continue
            seen.add(full_name)
            short_name = full_name.split('/')[-1]
            # Skip BugsInPy repos (already in eligible)
            in_bugsinpy = short_name in BUGSINPY_NAMES
            # E5+E6 (license OSS, not archived/fork/disabled)
            lic_obj = r.get('license') or {}
            lic_key = lic_obj.get('key', '').lower()
            e5_pass = lic_key in OSS_OK
            archived = r.get('isArchived', False)
            fork = r.get('isFork', False)
            disabled = r.get('isDisabled', False)
            e6_pass = not (archived or fork or disabled)

            row = {
                'full_name': full_name,
                'batch': label,
                'stars': r['stargazersCount'],
                'license': lic_key,
                'in_bugsinpy': in_bugsinpy,
                'e5_pass': e5_pass,
                'e6_pass': e6_pass,
                'py_bytes': 0,
                'loc_est': 0,
                'bucket': '',
                'small_candidate': False,
            }

            if not e5_pass or not e6_pass or in_bugsinpy:
                rows.append(row)
                continue

            # gh api languages
            py_bytes = get_python_bytes(full_name)
            row['py_bytes'] = py_bytes
            row['loc_est'] = py_bytes // 35
            loc = row['loc_est']
            if 1000 <= loc <= 5000:
                row['bucket'] = 'small_strict'
                row['small_candidate'] = True
            elif 500 <= loc < 1000:
                row['bucket'] = 'small_extended'
                row['small_candidate'] = True
            elif 5000 < loc <= 30000:
                row['bucket'] = 'medium'
            elif 30000 < loc <= 200000:
                row['bucket'] = 'large'
            else:
                row['bucket'] = 'out_of_range'
            rows.append(row)
            if i % 50 == 0:
                print(f"  ... processed {i}/{len(data)}")

    out_csv = ROOT / 'phase0_v2_candidates.csv'
    with out_csv.open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['full_name', 'batch', 'stars', 'license',
                                          'in_bugsinpy', 'e5_pass', 'e6_pass',
                                          'py_bytes', 'loc_est', 'bucket', 'small_candidate'])
        w.writeheader()
        w.writerows(rows)

    # Summary
    print(f"\n=== Summary ===")
    print(f"Total candidates examined: {len(rows)}")
    print(f"In BugsInPy (already eligible): {sum(1 for r in rows if r['in_bugsinpy'])}")
    print(f"E5 fail (license non-OSS): {sum(1 for r in rows if not r['e5_pass'] and not r['in_bugsinpy'])}")
    print(f"E6 fail (archived/fork/disabled): {sum(1 for r in rows if not r['e6_pass'] and r['e5_pass'])}")
    print(f"Out of range (LOC > 200k or < 500): {sum(1 for r in rows if r['bucket']=='out_of_range')}")
    print(f"BUCKET small_strict (1k-5k LOC): {sum(1 for r in rows if r['bucket']=='small_strict')}")
    print(f"BUCKET small_extended (500-1k LOC): {sum(1 for r in rows if r['bucket']=='small_extended')}")
    print(f"BUCKET medium (5k-30k LOC): {sum(1 for r in rows if r['bucket']=='medium')}")
    print(f"BUCKET large (30k-200k LOC): {sum(1 for r in rows if r['bucket']=='large')}")
    print(f"\nSmall candidates (any bucket): {sum(1 for r in rows if r['small_candidate'])}")

    # List small candidates
    small_list = sorted([r for r in rows if r['small_candidate']],
                         key=lambda x: (x['bucket'], -x['stars']))
    print(f"\n=== {len(small_list)} small candidates ===")
    for r in small_list:
        print(f"  [{r['bucket']:15}] {r['full_name']:50} {r['loc_est']:>5}LOC stars={r['stars']:>6} license={r['license']}")

    print(f"\nSaved: {out_csv}")


if __name__ == "__main__":
    main()
