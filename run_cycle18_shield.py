#!/usr/bin/env python3
"""Cycle 18 — forge --shield à scale. Mesure exit code + output cohérence."""
import json, re, subprocess, sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path('/home/sky/forge-case-studies')
CLONES = ROOT / 'clones'
BUGSINPY = CLONES / 'BugsInPy'
BENCH = ROOT / 'bench_v18' / 'results'
BENCH.mkdir(parents=True, exist_ok=True)
FORGE_BIN = '/home/sky/Bureau/forge/.venv/bin/forge'


def run(cmd, cwd=None, timeout=1800):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)


def get_buggy(case):
    proj = case['project']
    bug_n = case['bug_id'].split('-')[1]
    bug_info = BUGSINPY / 'projects' / proj / 'bugs' / bug_n / 'bug.info'
    if not bug_info.exists(): return None
    m = re.search(r'buggy_commit_id="([^"]+)"', bug_info.read_text())
    return m.group(1) if m else None


def clone_repo(url, name):
    target = CLONES / name
    if target.exists() and (target / '.git').exists():
        run(['git','reset','--hard'], cwd=target, timeout=60)
        for b in ('main','master','develop'):
            if run(['git','checkout',b], cwd=target, timeout=30).returncode == 0:
                break
        return target
    r = run(['git','clone','--quiet',url,str(target)], timeout=600)
    return target if r.returncode == 0 else None


def compute_pre_bug(repo, buggy):
    r = run(['git','show','-s','--format=%ci',buggy], cwd=repo)
    if r.returncode != 0:
        run(['git','fetch','origin',buggy], cwd=repo, timeout=120)
        r = run(['git','show','-s','--format=%ci',buggy], cwd=repo)
        if r.returncode != 0: return None
    bug_dt = datetime.strptime(r.stdout.strip()[:10], '%Y-%m-%d')
    cutoff = (bug_dt - timedelta(weeks=4)).strftime('%Y-%m-%d')
    r = run(['git','rev-list','-n','1',f'--before={cutoff}',buggy], cwd=repo)
    return r.stdout.strip() or None


def process_case(case, panel):
    bug_id = case['bug_id']
    out_dir = BENCH / panel / bug_id
    out_dir.mkdir(parents=True, exist_ok=True)
    out = dict(case); out['panel'] = panel; out['status'] = 'pending'
    print(f"\n=== {bug_id} ({panel}) ===", flush=True)
    try:
        buggy = get_buggy(case)
        if not buggy:
            out['status']='skip'; out['skip_reason']='bug_info_missing'
            return out
        repo = clone_repo(case['github_url'], case['project'])
        if not repo:
            out['status']='skip'; out['skip_reason']='clone_failed'
            return out
        pre_bug = compute_pre_bug(repo, buggy)
        if not pre_bug:
            out['status']='skip'; out['skip_reason']='shallow_history'
            return out
        run(['git','checkout','-q',pre_bug], cwd=repo, timeout=60)
        if not (repo / case['change_file']).is_file():
            out['status']='skip'; out['skip_reason']='file_missing_at_pre'
            return out

        # forge --shield with 600s timeout (1800 = full, but 600 reasonable to detect crash quickly)
        r = run([FORGE_BIN, '--shield', '.'], cwd=repo, timeout=600)
        (out_dir / 'shield.txt').write_text(r.stdout + '\n--- STDERR ---\n' + r.stderr)
        out['shield_exit'] = r.returncode
        out['stage1_present'] = 'STAGE 1' in r.stdout or 'carmack' in r.stdout.lower()
        out['stage2_present'] = 'STAGE 2' in r.stdout or 'gen-props' in r.stdout.lower() or 'gen_props' in r.stdout.lower()
        out['stage3_present'] = 'STAGE 3' in r.stdout or 'fast-deep' in r.stdout.lower() or 'fast_deep' in r.stdout.lower()
        out['stages_complete'] = out['stage1_present'] and out['stage2_present'] and out['stage3_present']
        out['status'] = 'ok'
        print(f"  shield exit={r.returncode} stages_complete={out['stages_complete']}", flush=True)
    except subprocess.TimeoutExpired:
        out['status']='skip'; out['skip_reason']='timeout_1800s'
        print(f"  TIMEOUT 600s", flush=True)
    except Exception as e:
        out['status']='error'; out['error']=str(e)
        print(f"  ERROR: {e}", flush=True)
    return out


def main():
    panel = sys.argv[1] if len(sys.argv) > 1 else 'train'
    start = 0; end = 9999
    for i, arg in enumerate(sys.argv):
        if arg == '--start': start = int(sys.argv[i+1])
        if arg == '--end': end = int(sys.argv[i+1])
    pf = 'panel_train_seed56.json' if panel == 'train' else 'panel_holdout_seed57.json'
    cases = json.loads((ROOT / pf).read_text())
    out_file = ROOT / f'results_v18_{panel}.jsonl'
    done = set()
    if out_file.exists():
        for l in out_file.read_text().splitlines():
            if l.strip(): done.add(json.loads(l)['bug_id'])
    with out_file.open('a') as f:
        for i, case in enumerate(cases):
            if i < start or i >= end: continue
            if case['bug_id'] in done:
                print(f"SKIP (done): {case['bug_id']}", flush=True)
                continue
            f.write(json.dumps(process_case(case, panel)) + '\n')
            f.flush()
    print(f"\nDONE.")


if __name__ == "__main__":
    main()
