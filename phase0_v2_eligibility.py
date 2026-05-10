#!/usr/bin/env python3
"""Phase 0 v2 step 2 — Deep eligibility check (E1-E4) on 52 small candidates.

For each candidate from phase0_v2_candidates.csv with small_candidate=True:
  E1 - Python ≥ 80% via gh api languages
  E2 - pytest via clone shallow + grep pyproject.toml/setup.py/tests
  E3 - ≥ 100 commits via git log
  E4 - ≥ 5 fix commits 2 years via git log --grep

Output: phase0_v2_small_eligible.csv with one row per candidate + verdict per criterion.
"""
import csv
import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path('/home/sky/forge-case-studies')
CLONES_TMP = ROOT / 'clones_tmp_v2'
CLONES_TMP.mkdir(exist_ok=True)


def run(cmd, cwd=None, timeout=60):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)


def check_e1_python_pct(full_name: str) -> tuple[bool, float]:
    r = run(['gh', 'api', f'repos/{full_name}/languages'])
    if r.returncode != 0 or not r.stdout.strip():
        return False, 0.0
    try:
        data = json.loads(r.stdout)
    except Exception:
        return False, 0.0
    total = sum(data.values())
    if total == 0:
        return False, 0.0
    py = data.get('Python', 0)
    pct = 100 * py / total
    return pct >= 80, pct


def clone_shallow(full_name: str) -> Path | None:
    short = full_name.split('/')[-1].replace('.', '_')
    target = CLONES_TMP / short
    if target.exists() and (target / '.git').exists():
        # Cleanup any half-done clone
        return target
    r = run(['git', 'clone', '--quiet', '--filter=blob:none',
             f'https://github.com/{full_name}.git', str(target)], timeout=120)
    if r.returncode != 0:
        return None
    return target


def check_e2_pytest(repo: Path) -> bool:
    # 1) pyproject.toml mentions pytest
    pyp = repo / 'pyproject.toml'
    if pyp.exists() and 'pytest' in pyp.read_text(errors='ignore').lower():
        return True
    # 2) setup.py mentions pytest
    setup = repo / 'setup.py'
    if setup.exists() and 'pytest' in setup.read_text(errors='ignore').lower():
        return True
    # 3) tests/ dir with test_*.py files
    for sub in ('tests', 'test'):
        d = repo / sub
        if d.is_dir():
            for p in d.rglob('test_*.py'):
                return True
            for p in d.rglob('*_test.py'):
                return True
    # 4) test_*.py at root or anywhere
    for p in repo.rglob('test_*.py'):
        # exclude nested dirs that aren't ours (e.g. /node_modules/)
        if '.git' in p.parts:
            continue
        return True
    return False


def check_e3_commits(repo: Path) -> int:
    r = run(['git', 'log', '--oneline'], cwd=repo, timeout=30)
    if r.returncode != 0:
        return 0
    return len(r.stdout.strip().splitlines())


def check_e4_fix_commits(repo: Path) -> int:
    r = run(['git', 'log', '--since=2 years ago', '--grep=fix\\|bug\\|regression',
             '--oneline'], cwd=repo, timeout=30)
    if r.returncode != 0:
        return 0
    return len(r.stdout.strip().splitlines())


def main():
    candidates = []
    with open(ROOT / 'phase0_v2_candidates.csv') as f:
        for r in csv.DictReader(f):
            if r['small_candidate'] == 'True':
                candidates.append(r)
    print(f"Phase 0 v2 step 2 — checking E1-E4 on {len(candidates)} small candidates\n")

    out_rows = []
    for i, c in enumerate(candidates, 1):
        full_name = c['full_name']
        bucket = c['bucket']
        loc = c['loc_est']
        print(f"[{i}/{len(candidates)}] {full_name:50} bucket={bucket} loc={loc} ", end='', flush=True)

        out = dict(c)
        out['e1_pass'] = False
        out['python_pct'] = 0.0
        out['e2_pass'] = False
        out['e3_commits'] = 0
        out['e3_pass'] = False
        out['e4_fix_2y'] = 0
        out['e4_pass'] = False
        out['eligible_v2'] = False
        out['fail_reasons'] = ''

        # E1 - Python ≥ 80%
        e1_pass, pct = check_e1_python_pct(full_name)
        out['e1_pass'] = e1_pass
        out['python_pct'] = round(pct, 1)
        if not e1_pass:
            out['fail_reasons'] = f'E1 (Python {pct:.1f}%<80%)'
            print(f"E1=FAIL ({pct:.1f}%)")
            out_rows.append(out)
            continue

        # Clone shallow
        repo = clone_shallow(full_name)
        if not repo:
            out['fail_reasons'] = 'clone_failed'
            print("clone_failed")
            out_rows.append(out)
            continue

        # E2 - pytest
        e2 = check_e2_pytest(repo)
        out['e2_pass'] = e2
        if not e2:
            out['fail_reasons'] = 'E2 (no pytest)'
            print(f"E1=OK E2=FAIL")
            out_rows.append(out)
            continue

        # E3 - ≥ 100 commits
        n_commits = check_e3_commits(repo)
        out['e3_commits'] = n_commits
        e3 = n_commits >= 100
        out['e3_pass'] = e3
        if not e3:
            out['fail_reasons'] = f'E3 (commits={n_commits}<100)'
            print(f"E1=OK E2=OK E3=FAIL ({n_commits})")
            out_rows.append(out)
            continue

        # E4 - ≥ 5 fix commits 2y
        n_fix = check_e4_fix_commits(repo)
        out['e4_fix_2y'] = n_fix
        e4 = n_fix >= 5
        out['e4_pass'] = e4
        if not e4:
            out['fail_reasons'] = f'E4 (fix_commits_2y={n_fix}<5)'
            print(f"E1=OK E2=OK E3=OK E4=FAIL ({n_fix})")
            out_rows.append(out)
            continue

        # All E1-E4 pass
        out['eligible_v2'] = True
        out['fail_reasons'] = ''
        print(f"ALL PASS! py={pct:.1f}% commits={n_commits} fix_2y={n_fix}")
        out_rows.append(out)

    # Save
    out_csv = ROOT / 'phase0_v2_small_eligible.csv'
    with out_csv.open('w', newline='') as f:
        fields = ['full_name', 'batch', 'stars', 'license', 'bucket', 'loc_est',
                  'e1_pass', 'python_pct', 'e2_pass', 'e3_commits', 'e3_pass',
                  'e4_fix_2y', 'e4_pass', 'eligible_v2', 'fail_reasons']
        w = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
        w.writeheader()
        w.writerows(out_rows)

    eligible = [r for r in out_rows if r['eligible_v2']]
    print(f"\n=== {len(eligible)} eligible after E1-E4 ===")
    for r in sorted(eligible, key=lambda x: -x['stars']):
        print(f"  [{r['bucket']:15}] {r['full_name']:50} loc={r['loc_est']:>5} py={r['python_pct']:>5}% commits={r['e3_commits']:>5} fix2y={r['e4_fix_2y']:>4}")

    print(f"\nSaved: {out_csv}")


if __name__ == "__main__":
    main()
