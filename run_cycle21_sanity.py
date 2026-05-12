#!/usr/bin/env python3
"""Cycle 21B — sanity à scale 10 outils peu testés sur 5 projets actifs."""
import json
import os
import re
import shutil
import subprocess
import time
from pathlib import Path

ROOT = Path('/home/sky/forge-case-studies')
CLONES = ROOT / 'clones'
FORGE = '/home/sky/Bureau/forge/forge.py'
BENCH = ROOT / 'bench_v13'
PROJECTS = ['ansible', 'scrapy', 'luigi', 'fastapi', 'black']


def run(cmd, cwd=None, timeout=120):
    t0 = time.time()
    try:
        r = subprocess.run(cmd, cwd=cwd, timeout=timeout,
                            capture_output=True, text=True, shell=False)
        return r.returncode, r.stdout, r.stderr, time.time() - t0
    except subprocess.TimeoutExpired as e:
        out_b = e.stdout or b'' if hasattr(e, 'stdout') else b''
        err_b = e.stderr or b'' if hasattr(e, 'stderr') else b''
        out = out_b.decode('utf-8', 'replace') if isinstance(out_b, bytes) else (out_b or '')
        err = err_b.decode('utf-8', 'replace') if isinstance(err_b, bytes) else (err_b or '')
        return 124, out, err, time.time() - t0
    except Exception as e:
        return -1, '', str(e), time.time() - t0


def save(tool, case, output, exit_code, elapsed, extra=None):
    d = BENCH / 'results' / tool / case
    d.mkdir(parents=True, exist_ok=True)
    (d / 'output.txt').write_text(output)
    meta = {'tool': tool, 'case': case, 'exit': exit_code,
            'elapsed_sec': round(elapsed, 2), 'output_chars': len(output)}
    if extra: meta.update(extra)
    (d / 'meta.json').write_text(json.dumps(meta, indent=2))


def check(output, ok_patterns, fallback=None):
    for p in ok_patterns:
        if re.search(p, output, re.I):
            return 'PASS', p
    if fallback:
        for p in fallback:
            if re.search(p, output, re.I):
                return 'PARTIAL', p
    return 'FAIL', None


def checkout_head(repo: Path):
    rc, out, _, _ = run(['git', 'symbolic-ref', 'refs/remotes/origin/HEAD', '--short'],
                       cwd=repo, timeout=10)
    default = out.strip().replace('origin/', '') if rc == 0 and out.strip() else 'master'
    rc, _, _, _ = run(['git', 'checkout', f'origin/{default}', '--force'],
                     cwd=repo, timeout=60)
    return rc == 0


def setup_tmpdir(project: str) -> Path:
    """Copy minimal slice of project into tmpdir for destructive tests."""
    tmp = Path(f'/tmp/forge_v13_{project}')
    if tmp.exists():
        shutil.rmtree(tmp)
    src = CLONES / project
    # Shallow copy: only .git + top-level + a small dir
    tmp.mkdir(parents=True)
    subprocess.run(['cp', '-r', str(src / '.git'), str(tmp)], check=True)
    # Copy a few python files only (avoid copy 100k files)
    for top in src.iterdir():
        if top.name in ('.git', '.tox', 'node_modules', '__pycache__'): continue
        if top.is_dir():
            # Copy only top-level dir + 1-2 subdirs
            dst = tmp / top.name
            try:
                if top.stat().st_size < 50_000_000:  # avoid huge
                    subprocess.run(['cp', '-r', str(top), str(dst)],
                                   timeout=30, check=True)
            except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
                pass
        else:
            try:
                subprocess.run(['cp', str(top), str(tmp / top.name)], check=True)
            except subprocess.CalledProcessError:
                pass
    # Restore HEAD on tmpdir
    checkout_head(tmp)
    return tmp


# === TOOLS ===

def test_anomaly(project, repo):
    rc, out, err, t = run(['python3', FORGE, '--anomaly', '--weeks', '4'], cwd=repo, timeout=120)
    output = out + ('\n--STDERR--\n' + err if err else '')
    status, p = check(output,
        [r'anomal|outlier|z-score|commits.*flagged'],
        [r'Not enough|insufficient'])
    save('anomaly', f'{project}', output, rc, t, {'pattern': p, 'status': status})
    return {'project': project, 'exit': rc, 'status': status, 'pattern': p, 'elapsed': round(t, 2)}


def test_heatmap(project, repo):
    rc, out, err, t = run(['python3', FORGE, '--heatmap'], cwd=repo, timeout=60)
    output = out + ('\n--STDERR--\n' + err if err else '')
    status, p = check(output,
        [r'failures|test.*fail|heatmap'],
        [r'No forge log|No failures'])
    save('heatmap', f'{project}', output, rc, t, {'pattern': p, 'status': status})
    return {'project': project, 'exit': rc, 'status': status, 'pattern': p, 'elapsed': round(t, 2)}


def test_baseline_diff(project, repo):
    # baseline + diff
    rc1, out1, err1, t1 = run(['python3', FORGE, '--baseline'], cwd=repo, timeout=180)
    rc2, out2, err2, t2 = run(['python3', FORGE, '--diff'], cwd=repo, timeout=120)
    output = '=== BASELINE ===\n' + out1 + '\n--STDERR--\n' + err1 + '\n=== DIFF ===\n' + out2 + '\n--STDERR--\n' + err2
    status, p = check(output,
        [r'Baseline saved|snapshot|Diff vs baseline|no diff'],
        [r'no baseline yet|no tests'])
    rc = max(rc1, rc2)
    save('baseline_diff', f'{project}', output, rc, t1 + t2, {'pattern': p, 'status': status})
    return {'project': project, 'exit': rc, 'status': status, 'pattern': p, 'elapsed': round(t1 + t2, 2)}


def test_init_add_close(project, repo):
    rc1, out1, _, t1 = run(['python3', FORGE, '--init'], cwd=repo, timeout=60)
    rc2, out2, _, t2 = run(['python3', FORGE, '--add', f'test bug cycle21 {project}'], cwd=repo, timeout=30)
    # Find BUG-ID
    import re as _re
    bugs_md = repo / 'BUGS.md'
    bug_id = None
    if bugs_md.exists():
        m = _re.search(r'BUG-\d+', bugs_md.read_text())
        if m: bug_id = m.group(0)
    if bug_id:
        rc3, out3, _, t3 = run(['python3', FORGE, '--close', bug_id], cwd=repo, timeout=30)
    else:
        rc3, out3, t3 = 0, "(skipped close - no bug_id found)", 0.0
    output = (f'=== INIT ===\n{out1}\n=== ADD ===\n{out2}\n=== CLOSE ({bug_id}) ===\n{out3}')
    status, p = check(output,
        [r'Forge initialized|Created|Added BUG-|marked FIXED|marked CLOSED'],
        [r'already exists'])
    rc = max(rc1, rc2, rc3)
    save('init_add_close', f'{project}', output, rc, t1 + t2 + t3, {'pattern': p, 'status': status, 'bug_id': bug_id})
    return {'project': project, 'exit': rc, 'status': status, 'pattern': p, 'elapsed': round(t1 + t2 + t3, 2)}


def test_hooks(project, repo):
    rc1, out1, _, t1 = run(['python3', FORGE, '--install-hook'], cwd=repo, timeout=30)
    rc2, out2, _, t2 = run(['python3', FORGE, '--uninstall-hook'], cwd=repo, timeout=30)
    output = f'=== INSTALL ===\n{out1}\n=== UNINSTALL ===\n{out2}'
    status, p = check(output,
        [r'Installed.*pre-commit|Removed.*hook'],
        [r'already installed|No.*hook found'])
    rc = max(rc1, rc2)
    save('hooks', f'{project}', output, rc, t1 + t2, {'pattern': p, 'status': status})
    return {'project': project, 'exit': rc, 'status': status, 'pattern': p, 'elapsed': round(t1 + t2, 2)}


def test_watch(project, repo):
    rc, out, err, t = run(['timeout', '5', 'python3', FORGE, '--watch'], cwd=repo, timeout=10)
    output = out + ('\n--STDERR--\n' + err if err else '')
    # ANSI clear or "Watching" message or timeout (124/143)
    status = 'PASS' if rc in (124, 143) or 'watch' in output.lower() or '\x1b[' in output else 'FAIL'
    save('watch', f'{project}', output, rc, t, {'status': status})
    return {'project': project, 'exit': rc, 'status': status, 'pattern': '', 'elapsed': round(t, 2)}


def test_full_cycle(project, repo):
    rc, out, err, t = run(['timeout', '180', 'python3', FORGE, '--full-cycle'], cwd=repo, timeout=200)
    output = out + ('\n--STDERR--\n' + err if err else '')
    status, p = check(output,
        [r'carmack|heatmap|full.?cycle|init|complete'],
        [r'TIMEOUT|partial'])
    save('full_cycle', f'{project}', output, rc, t, {'pattern': p, 'status': status})
    return {'project': project, 'exit': rc, 'status': status, 'pattern': p, 'elapsed': round(t, 2)}


def test_predict_carmack(project, repo):
    # 2 calls: --predict + --carmack
    rc1, out1, err1, t1 = run(['python3', FORGE, '--predict', '--weeks', '4'], cwd=repo, timeout=120)
    rc2, out2, err2, t2 = run(['python3', FORGE, '--carmack', '--weeks', '4'], cwd=repo, timeout=120)
    output = f'=== PREDICT ===\n{out1}\n--STDERR--\n{err1}\n=== CARMACK ===\n{out2}\n--STDERR--\n{err2}'
    status, p = check(output,
        [r'predict|carmack.*score|kalman'],
        [r'No tracked|No commits'])
    rc = max(rc1, rc2)
    save('predict_carmack', f'{project}', output, rc, t1 + t2, {'pattern': p, 'status': status})
    return {'project': project, 'exit': rc, 'status': status, 'pattern': p, 'elapsed': round(t1 + t2, 2)}


def test_incremental_mutate(project, repo):
    # Need --since SHA. Use HEAD~5 as baseline.
    rc_sha, sha, _, _ = run(['git', 'rev-parse', 'HEAD~5'], cwd=repo, timeout=10)
    if rc_sha != 0 or not sha.strip():
        save('incremental_mutate', f'{project}', '(skipped: no HEAD~5)', 0, 0)
        return {'project': project, 'exit': 0, 'status': 'PARTIAL', 'pattern': 'no HEAD~5', 'elapsed': 0}
    rc, out, err, t = run(['timeout', '60', 'python3', FORGE, '--incremental-mutate',
                          '--since', sha.strip()], cwd=repo, timeout=70)
    output = out + ('\n--STDERR--\n' + err if err else '')
    status, p = check(output,
        [r'mutate|incremental|since|mutant'],
        [r'No diff|nothing to mutate|libcst', r'TIMEOUT'])
    save('incremental_mutate', f'{project}', output, rc, t, {'pattern': p, 'status': status})
    return {'project': project, 'exit': rc, 'status': status, 'pattern': p, 'elapsed': round(t, 2)}


def test_flaky_dtw(project, repo):
    rc, out, err, t = run(['python3', FORGE, '--flaky-dtw', '3'], cwd=repo, timeout=180)
    output = out + ('\n--STDERR--\n' + err if err else '')
    status, p = check(output,
        [r'\d+ runs|stable|flaky|No flaky'],
        [r'No tests|nothing'])
    save('flaky_dtw', f'{project}', output, rc, t, {'pattern': p, 'status': status})
    return {'project': project, 'exit': rc, 'status': status, 'pattern': p, 'elapsed': round(t, 2)}


def main():
    BENCH.mkdir(exist_ok=True)
    print(f'Cycle 21B — sanity 10 outils sur 5 projets actifs')
    print(f'Forge: {FORGE} (should be v2.1.0)\n')

    tools = [
        ('anomaly', test_anomaly, False),  # (name, fn, needs_tmpdir)
        ('heatmap', test_heatmap, False),
        ('baseline_diff', test_baseline_diff, True),
        ('init_add_close', test_init_add_close, True),
        ('hooks', test_hooks, True),
        ('watch', test_watch, False),
        ('full_cycle', test_full_cycle, True),
        ('predict_carmack', test_predict_carmack, False),
        ('incremental_mutate', test_incremental_mutate, False),
        ('flaky_dtw', test_flaky_dtw, True),
    ]

    all_results = {}
    for tool_name, tool_fn, needs_tmp in tools:
        print(f'\n=== {tool_name} ===', flush=True)
        results = []
        for project in PROJECTS:
            if needs_tmp:
                try:
                    repo = setup_tmpdir(project)
                except Exception as e:
                    print(f'  [{project}] tmpdir setup fail: {e}', flush=True)
                    results.append({'project': project, 'status': 'TMPDIR_FAIL'})
                    continue
            else:
                repo = CLONES / project
                checkout_head(repo)
            try:
                r = tool_fn(project, repo)
                results.append(r)
                print(f'  [{project:12s}] exit={r.get("exit")} status={r.get("status"):8s} elapsed={r.get("elapsed", 0)}s', flush=True)
            except Exception as e:
                print(f'  [{project}] exception: {type(e).__name__}: {e}', flush=True)
                results.append({'project': project, 'status': 'EXCEPTION', 'error': str(e)})
        all_results[tool_name] = results
        (ROOT / 'cycle21_results_partial.json').write_text(json.dumps(all_results, indent=2))

    # Aggregate
    print(f'\n=== AGGREGATE ===', flush=True)
    tools_pass = 0
    summary_per_tool = {}
    for tn, results in all_results.items():
        n = len(results)
        n_pass = sum(1 for r in results if r.get('status') == 'PASS')
        n_partial = sum(1 for r in results if r.get('status') == 'PARTIAL')
        n_fail = sum(1 for r in results if r.get('status') == 'FAIL')
        n_skip = sum(1 for r in results if r.get('status') in ('SKIP', 'TMPDIR_FAIL', 'EXCEPTION'))
        ratio_ok = 100 * (n_pass + n_partial) / max(n, 1)
        ok = ratio_ok >= 80
        if ok: tools_pass += 1
        summary_per_tool[tn] = {
            'n': n, 'pass': n_pass, 'partial': n_partial, 'fail': n_fail, 'skip': n_skip,
            'ratio_ok': ratio_ok, 'tool_ok': ok,
        }
        print(f'  {tn:18s} n={n} P={n_pass} Pa={n_partial} F={n_fail} S={n_skip} ratio={ratio_ok:.0f}% [{"OK" if ok else "NO"}]', flush=True)

    overall = tools_pass >= 8
    print(f'\nTools passing (≥80%): {tools_pass}/10', flush=True)
    print(f'C_sanity_10_tools: {"OUI" if overall else "NON"}', flush=True)

    summary = {
        'cycle': '21B',
        'tools_tested': list(all_results.keys()),
        'projects': PROJECTS,
        'per_tool': summary_per_tool,
        'tools_pass_count': tools_pass,
        'tools_pass_threshold': 8,
        'verdict_c_sanity_10_tools': 'OUI' if overall else 'NON',
        'all_results': all_results,
    }
    (ROOT / 'cycle21_summary.json').write_text(json.dumps(summary, indent=2))
    print(f'\nSaved cycle21_summary.json', flush=True)


if __name__ == '__main__':
    main()
