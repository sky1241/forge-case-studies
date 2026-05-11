#!/usr/bin/env python3
"""Cycle 16 — measure if cold-start similarity signal improves carmack ranking.

For each cold-start case (bugfixes < 3 on change_file):
1. Run forge.predict_carmack normally → baseline rank
2. For each file in repo, compute _compute_similarity_score using
   files with top bugfix counts as buggy_files
3. Recompose carmack score with: blend = 0.5 * complexity + 0.5 * similarity
   (replace complexity weight contribution with this blend)
4. New rank = position of change_file in resorted list
5. Compare baseline rank vs blend rank → measure improvement

Usage: python3 run_cycle16.py [train|holdout|reference]
"""
import json
import math
import random
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, '/home/sky/Bureau/forge')
import forge

ROOT = Path('/home/sky/forge-case-studies')
CLONES = ROOT / 'clones'
BUGSINPY = CLONES / 'BugsInPy'
BENCH = ROOT / 'bench_v16' / 'results'
BENCH.mkdir(parents=True, exist_ok=True)
CUTOFF_WEEKS = 4


def run(cmd, cwd=None, timeout=600):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)


def get_buggy_commit(case):
    proj = case['project']
    bug_n = case['bug_id'].split('-')[1]
    bug_info = BUGSINPY / 'projects' / proj / 'bugs' / bug_n / 'bug.info'
    if not bug_info.exists():
        return None
    import re
    m = re.search(r'buggy_commit_id="([^"]+)"', bug_info.read_text())
    return m.group(1) if m else None


def clone_full(github_url, project_name):
    target = CLONES / project_name
    if target.exists() and (target / '.git').exists():
        run(['git', 'reset', '--hard'], cwd=target, timeout=60)
        for b in ('main', 'master', 'develop'):
            if run(['git', 'checkout', b], cwd=target, timeout=30).returncode == 0:
                break
        return target
    r = run(['git', 'clone', '--quiet', github_url, str(target)], timeout=600)
    if r.returncode != 0:
        return None
    return target


def compute_pre_bug(repo, buggy_commit):
    r = run(['git', 'show', '-s', '--format=%ci', buggy_commit], cwd=repo)
    if r.returncode != 0:
        run(['git', 'fetch', 'origin', buggy_commit], cwd=repo, timeout=120)
        r = run(['git', 'show', '-s', '--format=%ci', buggy_commit], cwd=repo)
        if r.returncode != 0:
            return None, None
    bug_iso = r.stdout.strip()
    bug_dt = datetime.strptime(bug_iso[:10], '%Y-%m-%d')
    cutoff = (bug_dt - timedelta(weeks=CUTOFF_WEEKS)).strftime('%Y-%m-%d')
    r = run(['git', 'rev-list', '-n', '1', f'--before={cutoff}', buggy_commit], cwd=repo)
    pre = r.stdout.strip()
    return cutoff, pre


def find_rank(results, target_file):
    for i, r in enumerate(results, 1):
        if r['file'] == target_file:
            return i
    return None


def process_case(case, panel_label):
    bug_id = case['bug_id']
    project = case['project']
    out_dir = BENCH / panel_label / bug_id
    out_dir.mkdir(parents=True, exist_ok=True)
    out = dict(case)
    out['panel'] = panel_label

    print(f"\n=== {bug_id} ({panel_label}) ===", flush=True)
    try:
        buggy = get_buggy_commit(case)
        if not buggy:
            out['status'] = 'skip'; out['skip_reason'] = 'bug_info_missing'
            return out
        repo = clone_full(case['github_url'], project)
        if not repo:
            out['status'] = 'skip'; out['skip_reason'] = 'clone_failed'
            return out
        cutoff, pre_bug = compute_pre_bug(repo, buggy)
        if not pre_bug:
            out['status'] = 'skip'; out['skip_reason'] = 'shallow_history'
            return out
        out['pre_bug_commit'] = pre_bug
        out['cutoff_date'] = cutoff
        run(['git', 'checkout', '-q', pre_bug], cwd=repo, timeout=60)

        change_file = case['change_file']
        if not (repo / change_file).is_file():
            out['status'] = 'skip'; out['skip_reason'] = 'file_missing_at_pre'
            return out

        # Baseline: standard predict_carmack
        results = forge.predict_carmack(repo, weeks=999)
        if not results:
            out['status'] = 'skip'; out['skip_reason'] = 'forge_crashed'
            return out
        out['total_files'] = len(results)
        out['rank_baseline'] = find_rank(results, change_file)

        # Compute similarity for ALL files using top bugfix files as buggy_files
        # Top 20% bugfix files = buggy reference
        sorted_by_bf = sorted(results, key=lambda r: r.get('bugfixes', 0), reverse=True)
        top_n_bf = max(1, len(sorted_by_bf) // 5)
        buggy_files = [Path(r['file']) for r in sorted_by_bf[:top_n_bf]
                       if r.get('bugfixes', 0) >= 1]

        # Compute similarity per file + new composite score
        for r in results:
            try:
                r['similarity'] = forge._compute_similarity_score(
                    repo / r['file'], repo, buggy_files
                )
            except Exception:
                r['similarity'] = 0.0
            # New score: same as baseline but replace complexity weight slot with
            # blend(complexity, similarity)
            old_complexity_contrib = r.get('cold_start_regime', 'history')
            # For simplicity: just blend complexity + similarity equally in r["score"]
            # We override the "score" field with a new computation:
            # Use stored score but add similarity * 0.15 (replacing complexity * 0.15 effectively)
            # Actually we recompute: same weights except complexity slot = 0.5*complexity + 0.5*similarity
            # The carmack composite stored is `score` so we adjust:
            old_complexity = r.get('complexity', 0)
            blend = 0.5 * old_complexity + 0.5 * r['similarity']
            # Composite delta: replace complexity's 0.15 contribution with blend's 0.15
            # delta = 0.15 * (blend - old_complexity_normalized)
            # But complexity was already normalized in [0,1] same as blend
            r['score_with_sim'] = r['score'] - 0.15 * old_complexity + 0.15 * blend

        # Re-rank by score_with_sim
        results_resorted = sorted(results, key=lambda r: r['score_with_sim'], reverse=True)
        out['rank_with_similarity'] = find_rank(results_resorted, change_file)
        out['baseline_top10'] = bool(out['rank_baseline'] and out['rank_baseline'] <= 10)
        out['with_sim_top10'] = bool(out['rank_with_similarity'] and out['rank_with_similarity'] <= 10)

        # Save full results
        (out_dir / 'carmack_with_sim.json').write_text(json.dumps({
            'bug_id': bug_id, 'change_file': change_file,
            'rank_baseline': out['rank_baseline'],
            'rank_with_similarity': out['rank_with_similarity'],
            'top_bugfix_files_used': [str(p) for p in buggy_files],
            'total_files': len(results),
        }, indent=2))

        out['status'] = 'ok'
        print(f"  baseline_rank={out['rank_baseline']} sim_rank={out['rank_with_similarity']} delta={out['rank_baseline'] - out['rank_with_similarity'] if out['rank_baseline'] and out['rank_with_similarity'] else 'N/A'}", flush=True)
    except subprocess.TimeoutExpired as e:
        out['status'] = 'skip'; out['skip_reason'] = 'forge_crashed'
        out['skip_detail'] = f'timeout {e}'
    except Exception as e:
        out['status'] = 'error'; out['error'] = str(e)
        print(f"  ERROR: {e}", flush=True)
    return out


def main():
    panel = sys.argv[1] if len(sys.argv) > 1 else 'train'
    start = 0; end = 9999
    for i, arg in enumerate(sys.argv):
        if arg == '--start': start = int(sys.argv[i+1])
        if arg == '--end': end = int(sys.argv[i+1])

    files_map = {
        'train': 'panel_train_seed52.json',
        'holdout': 'panel_holdout_seed53.json',
        'reference': 'panel_reference.json',
    }
    panel_file = files_map[panel]
    cases = json.loads((ROOT / panel_file).read_text())
    print(f"Cycle 16 — {panel.upper()}: {len(cases)} cases [start={start}, end={end}]\n", flush=True)

    out_file = ROOT / f'results_v16_v2_{panel}.jsonl'
    done = set()
    if out_file.exists():
        for line in out_file.read_text().splitlines():
            if line.strip():
                done.add(json.loads(line)['bug_id'])
    with out_file.open('a') as f:
        for i, case in enumerate(cases):
            if i < start or i >= end: continue
            if case['bug_id'] in done:
                print(f"SKIP (done): {case['bug_id']}", flush=True)
                continue
            result = process_case(case, panel)
            f.write(json.dumps(result) + '\n')
            f.flush()
    print(f"\nChunk DONE.")


if __name__ == "__main__":
    main()
