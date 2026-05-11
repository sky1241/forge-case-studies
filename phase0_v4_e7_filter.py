#!/usr/bin/env python3
"""Phase 0 v4 (cycle 13) — Filter all eligible bugs by E7 (≥3 bugfix commits on change_file before PRE_BUG).

Input: all bugs eligible E1-E6 (BugsInPy 13 projets + 6 small fallback eligibles).
Output: phase0_v4_e7_eligible.csv with E7 result per bug + count of fix commits.

Then sample panel with seeds 46/47 from E7-eligible bugs only.
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
CLONES = ROOT / 'clones'
CLONES_TMP = ROOT / 'clones_tmp_v2'
CUTOFF_WEEKS = 4

# Same eligible set as v3
SMALL_ELIGIBLE = [
    'sherlock-project/sherlock', 'lm-sys/RouteLLM', 'pudo/dataset',
    'MechanicalSoup/MechanicalSoup', 'blocklistproject/Lists', 'Bing-su/adetailer',
]
BUGSINPY_ELIGIBLE = {
    'medium': ['cookiecutter', 'httpie', 'PySnooper', 'thefuck'],
    'large':  ['ansible', 'black', 'fastapi', 'luigi', 'scrapy', 'tornado', 'youtube-dl'],
}
BUGSINPY_GITHUB_URLS = {
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
        if not p.endswith('.py'): continue
        base = p.split('/')[-1]
        if base.startswith('test_') or base.endswith('_test.py') or '/tests/' in p or '/test/' in p:
            continue
        return p
    for p in diffs:
        if p.endswith('.py'): return p
    return None


def list_bugsinpy_bugs() -> list[dict]:
    out = []
    for bucket, projects in BUGSINPY_ELIGIBLE.items():
        for proj in projects:
            bugs_dir = BUGSINPY / 'projects' / proj / 'bugs'
            if not bugs_dir.exists(): continue
            for bug_dir in sorted(bugs_dir.iterdir(), key=lambda p: int(p.name) if p.name.isdigit() else 999):
                if not bug_dir.is_dir(): continue
                info_file = bug_dir / 'bug.info'
                if not info_file.exists(): continue
                info = parse_bug_info(info_file)
                cf = parse_change_file(bug_dir)
                if not cf: continue
                out.append({
                    'project': proj, 'bug_id': f'{proj}-{bug_dir.name}',
                    'github_url': BUGSINPY_GITHUB_URLS[proj], 'bucket': bucket,
                    'buggy_commit': info.get('buggy_commit_id', ''),
                    'fixed_commit': info.get('fixed_commit_id', ''),
                    'change_file': cf,
                    'source': 'BugsInPy',
                })
    return out


def ensure_clone(github_url: str, project_name: str) -> Path | None:
    for parent in (CLONES, CLONES_TMP):
        target = parent / project_name
        if target.exists() and (target / '.git').exists():
            return target
    target = CLONES / project_name
    r = run(['git', 'clone', '--quiet', github_url, str(target)], timeout=600)
    if r.returncode != 0:
        return None
    return target


def check_e7(bug: dict) -> dict:
    """Return dict with e7_pass, fix_count, pre_bug_date, skip_reason."""
    out = dict(bug)
    out['e7_pass'] = False
    out['fix_count'] = 0
    out['pre_bug_date'] = ''
    out['skip_reason'] = ''

    repo = ensure_clone(bug['github_url'], bug['project'])
    if not repo:
        out['skip_reason'] = 'clone_failed'
        return out

    # Try to resolve buggy_commit
    r = run(['git', 'show', '-s', '--format=%ci', bug['buggy_commit']], cwd=repo)
    if r.returncode != 0:
        run(['git', 'fetch', 'origin', bug['buggy_commit']], cwd=repo, timeout=120)
        r = run(['git', 'show', '-s', '--format=%ci', bug['buggy_commit']], cwd=repo)
        if r.returncode != 0:
            out['skip_reason'] = 'bug_commit_missing'
            return out
    bug_iso = r.stdout.strip()
    bug_dt = datetime.strptime(bug_iso[:10], '%Y-%m-%d')
    cutoff = (bug_dt - timedelta(weeks=CUTOFF_WEEKS)).strftime('%Y-%m-%d')
    r = run(['git', 'rev-list', '-n', '1', f'--before={cutoff}', bug['buggy_commit']], cwd=repo)
    pre_bug = r.stdout.strip()
    if not pre_bug:
        out['skip_reason'] = 'shallow_history'
        return out

    # Get PRE_BUG date
    r = run(['git', 'show', '-s', '--format=%ci', pre_bug], cwd=repo)
    pre_bug_iso = r.stdout.strip()
    out['pre_bug_date'] = pre_bug_iso

    # E7: count bugfix commits before PRE_BUG on change_file
    r = run(['git', 'log', f'--until={pre_bug_iso}',
             '--grep=fix\\|bug\\|patch\\|regression', '-i', '--oneline',
             '--', bug['change_file']], cwd=repo, timeout=60)
    if r.returncode == 0:
        out['fix_count'] = len([l for l in r.stdout.strip().splitlines() if l.strip()])
    else:
        out['fix_count'] = 0

    if out['fix_count'] >= 3:
        out['e7_pass'] = True
    else:
        out['skip_reason'] = 'cold_start_blind_e7'
    return out


def main():
    bugs = list_bugsinpy_bugs()
    print(f"Phase 0 v4 — E7 filter on {len(bugs)} BugsInPy bugs eligible E1-E6\n")

    results = []
    for i, b in enumerate(bugs, 1):
        if i % 25 == 0:
            print(f"  ... {i}/{len(bugs)} done", flush=True)
        r = check_e7(b)
        results.append(r)

    # Save CSV
    out_csv = ROOT / 'phase0_v4_e7_eligible.csv'
    with out_csv.open('w', newline='') as f:
        fields = ['project', 'bug_id', 'bucket', 'change_file', 'buggy_commit',
                  'pre_bug_date', 'fix_count', 'e7_pass', 'skip_reason']
        w = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
        w.writeheader()
        w.writerows(results)

    # Summary
    eligible = [r for r in results if r['e7_pass']]
    print(f"\n=== Summary ===")
    print(f"Total bugs examined: {len(results)}")
    print(f"E7 PASS (≥3 fix commits on file before PRE_BUG): {len(eligible)}")
    print(f"E7 FAIL by reason:")
    by_reason = {}
    for r in results:
        if not r['e7_pass']:
            by_reason[r['skip_reason']] = by_reason.get(r['skip_reason'], 0) + 1
    for k, v in sorted(by_reason.items()):
        print(f"  {k}: {v}")
    print()
    print(f"=== Eligible per bucket ===")
    by_bucket = {}
    for r in eligible:
        by_bucket[r['bucket']] = by_bucket.get(r['bucket'], 0) + 1
    for b, n in sorted(by_bucket.items()):
        print(f"  {b}: {n} bugs eligible E1-E7")

    # Save eligible bugs (json) for sampling
    (ROOT / 'phase0_v4_e7_pool.json').write_text(json.dumps(eligible, indent=2))
    print(f"\nSaved {out_csv} + phase0_v4_e7_pool.json")


if __name__ == "__main__":
    main()
