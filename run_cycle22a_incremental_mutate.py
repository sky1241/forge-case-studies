#!/usr/bin/env python3
"""Cycle 22A — Refaire test incremental_mutate proprement.

Cycle 21B was bogus: ran `forge --incremental-mutate` alone → ERROR usage,
pattern regex matched "incremental-mutate" word in the error → false PASS.

This run: each project gets a real diff via fake commit + restore.
"""
import json
import re
import subprocess
import time
from pathlib import Path

ROOT = Path('/home/sky/forge-case-studies')
CLONES = ROOT / 'clones'
FORGE = '/home/sky/Bureau/forge/forge.py'
PYTHON = '/home/sky/Bureau/forge/.venv/bin/python3'  # venv has libcst installed
BENCH = ROOT / 'bench_v13' / 'results' / 'incremental_mutate'
PROJECTS = ['ansible', 'scrapy', 'luigi', 'fastapi', 'black']


def run(cmd, cwd=None, timeout=120):
    t0 = time.time()
    try:
        r = subprocess.run(cmd, cwd=cwd, timeout=timeout,
                            capture_output=True, text=True, shell=False)
        return r.returncode, r.stdout, r.stderr, time.time() - t0
    except subprocess.TimeoutExpired as e:
        out = (e.stdout or b'').decode('utf-8', 'replace') if isinstance(e.stdout, bytes) else (e.stdout or '')
        err = (e.stderr or b'').decode('utf-8', 'replace') if isinstance(e.stderr, bytes) else (e.stderr or '')
        return 124, out, err, time.time() - t0


def checkout_head(repo):
    rc, out, _, _ = run(['git', 'symbolic-ref', 'refs/remotes/origin/HEAD', '--short'],
                       cwd=repo, timeout=10)
    default = out.strip().replace('origin/', '') if rc == 0 and out.strip() else 'master'
    rc, _, _, _ = run(['git', 'checkout', f'origin/{default}', '--force'],
                     cwd=repo, timeout=60)
    return rc == 0


def find_small_py_file(repo: Path) -> Path | None:
    """Find a small Python file (10-100 LOC) to mutate."""
    candidates = []
    for p in repo.rglob('*.py'):
        if 'test' in p.name.lower() or '__init__' in p.name: continue
        if any(s in str(p) for s in ('.tox', '.venv', 'site-packages', '__pycache__')): continue
        try:
            lines = p.read_text(encoding='utf-8', errors='replace').splitlines()
            loc = len([l for l in lines if l.strip() and not l.strip().startswith('#')])
            if 10 <= loc <= 100:
                if any(l.strip().startswith('def ') for l in lines):
                    candidates.append((p, loc))
        except (UnicodeDecodeError, PermissionError):
            continue
        if len(candidates) >= 10: break
    if not candidates: return None
    candidates.sort(key=lambda x: abs(x[1] - 40))
    return candidates[0][0]


def test_one(project: str) -> dict:
    """Real test: edit + commit + forge --mutate --incremental-mutate --since HEAD~1."""
    repo = CLONES / project
    if not repo.is_dir():
        return {'project': project, 'status': 'NO_CLONE'}

    checkout_head(repo)
    target_full = find_small_py_file(repo)
    if not target_full:
        return {'project': project, 'status': 'NO_TARGET'}
    target = target_full.relative_to(repo)

    # Make a real diff: append trivial line + commit
    original_content = target_full.read_text(encoding='utf-8', errors='replace')
    target_full.write_text(original_content + "\n# cycle22a test diff\n")
    rc_add, _, err_add, _ = run(['git', 'add', '-A'], cwd=repo, timeout=30)
    rc_commit, out_commit, err_commit, _ = run(
        ['git', 'commit', '-q', '-m', 'cycle22a test diff for incremental-mutate'],
        cwd=repo, timeout=30
    )
    if rc_commit != 0:
        # restore + bail
        run(['git', 'checkout', '--', str(target)], cwd=repo, timeout=10)
        return {'project': project, 'status': 'COMMIT_FAIL', 'err': err_commit[:200]}

    # Real command
    rc, stdout, stderr, t = run(
        [PYTHON, FORGE, '--mutate', '--incremental-mutate',
         '--since', 'HEAD~1', '--paths-to-mutate', str(target)],
        cwd=repo, timeout=180
    )
    output = stdout + ('\n--STDERR--\n' + stderr if stderr else '')

    # Save verbatim
    out_dir = BENCH / project
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / 'output.txt').write_text(output)
    (out_dir / 'meta.json').write_text(json.dumps({
        'project': project,
        'cmd': f'forge --mutate --incremental-mutate --since HEAD~1 --paths-to-mutate {target}',
        'target_file': str(target),
        'exit': rc,
        'elapsed_sec': round(t, 2),
        'output_chars': len(output),
        'cycle': '22A_REAL_TEST',
    }, indent=2))

    # Restore: hard reset to HEAD~1 (the test commit we just made)
    run(['git', 'reset', '--hard', 'HEAD~1'], cwd=repo, timeout=30)

    # Classify status:
    # - exit 0 OR 1 (normal mutate exit) + output mentions incremental_mutate logic = PASS
    # - exit 0 + "libcst" missing = PARTIAL (graceful skip)
    # - exit != 0/1 OR output = "ERROR usage" = FAIL
    is_usage_err = 'ERROR' in output and 'Usage' in output
    is_libcst_missing = 'libcst' in output.lower() and ('require' in output.lower() or 'install' in output.lower())
    real_pattern = bool(re.search(r'mutant|mutate|incremental|since.*HEAD|lines.*mutated|0 surviving', output, re.I)) and not is_usage_err

    if is_usage_err:
        status = 'FAIL_USAGE_ERR'
    elif is_libcst_missing:
        status = 'PARTIAL_LIBCST_MISSING'
    elif real_pattern and rc in (0, 1):
        status = 'PASS'
    else:
        status = 'FAIL_OTHER'

    return {
        'project': project,
        'cmd': f'forge --mutate --incremental-mutate --since HEAD~1 --paths-to-mutate {target}',
        'target_file': str(target),
        'exit': rc,
        'status': status,
        'elapsed': round(t, 2),
        'output_chars': len(output),
        'is_usage_err': is_usage_err,
        'is_libcst_missing': is_libcst_missing,
    }


def main():
    BENCH.mkdir(parents=True, exist_ok=True)
    print(f'Cycle 22A — incremental_mutate REAL TEST on {len(PROJECTS)} projects')
    results = []
    for project in PROJECTS:
        print(f'\n[{project}]', flush=True)
        r = test_one(project)
        results.append(r)
        print(f'  exit={r.get("exit")} status={r.get("status"):25s} '
              f'target={r.get("target_file", "?")[:50]} '
              f'elapsed={r.get("elapsed", 0)}s', flush=True)

    # Aggregate
    n = len(results)
    n_pass = sum(1 for r in results if r.get('status') == 'PASS')
    n_partial = sum(1 for r in results if r.get('status', '').startswith('PARTIAL'))
    n_fail = sum(1 for r in results if r.get('status', '').startswith('FAIL'))
    ratio_ok = 100 * (n_pass + n_partial) / max(n, 1)

    print(f'\n=== AGGREGATE ===')
    print(f'PASS:    {n_pass}/{n}')
    print(f'PARTIAL: {n_partial}/{n}')
    print(f'FAIL:    {n_fail}/{n}')
    print(f'ratio_ok: {ratio_ok:.1f}%')
    verdict = 'OUI' if ratio_ok >= 80 else 'NON'
    print(f'Verdict (≥80%): {verdict}')

    summary = {
        'cycle': '22A_incremental_mutate_REAL',
        'n_total': n,
        'n_pass': n_pass,
        'n_partial': n_partial,
        'n_fail': n_fail,
        'ratio_ok': ratio_ok,
        'verdict': verdict,
        'methodology': 'real diff via test commit + restore. Cycle 21B was bogus (ran --incremental-mutate without --mutate, pattern matched ERROR usage word).',
        'results': results,
    }
    (ROOT / 'cycle22a_summary.json').write_text(json.dumps(summary, indent=2))
    print(f'\nSaved cycle22a_summary.json')


if __name__ == '__main__':
    main()
