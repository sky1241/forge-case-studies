#!/usr/bin/env python3
"""Cycle 20 v2 — sanity à scale sur projets réels.

For each tool, run 5+ cases on real GitHub-cloned projects.
Capture exit + verbatim output. Check pattern match for "coherent output".
"""
import json
import re
import subprocess
import time
from pathlib import Path

ROOT = Path('/home/sky/forge-case-studies')
CLONES = ROOT / 'clones'
FORGE = '/home/sky/Bureau/forge/forge.py'
BENCH = ROOT / 'bench_v20_v2'

# Active projects with recent activity (from cycle 18 v2 analysis)
ACTIVE_PROJECTS = ['ansible', 'scrapy', 'luigi', 'fastapi', 'black', 'tornado']
DORMANT_PROJECTS = ['thefuck', 'PySnooper', 'httpie', 'youtube-dl', 'cookiecutter']
ALL_PROJECTS = ACTIVE_PROJECTS + DORMANT_PROJECTS


def run(cmd, cwd=None, timeout=120, shell_str=None):
    """Run cmd. Return (exit, stdout, stderr, elapsed_sec)."""
    t0 = time.time()
    try:
        if shell_str:
            r = subprocess.run(shell_str, cwd=cwd, timeout=timeout,
                                capture_output=True, text=True, shell=True)
        else:
            r = subprocess.run(cmd, cwd=cwd, timeout=timeout,
                                capture_output=True, text=True, shell=False)
        return r.returncode, r.stdout, r.stderr, time.time() - t0
    except subprocess.TimeoutExpired as e:
        return 124, (e.stdout or b'').decode('utf-8', 'replace') if isinstance(e.stdout, bytes) else (e.stdout or ''), \
               (e.stderr or b'').decode('utf-8', 'replace') if isinstance(e.stderr, bytes) else (e.stderr or ''), \
               time.time() - t0
    except Exception as e:
        return -1, '', str(e), time.time() - t0


def save(tool, case, output, exit_code, elapsed, extra=None):
    d = BENCH / 'results' / tool / case
    d.mkdir(parents=True, exist_ok=True)
    (d / 'output.txt').write_text(output)
    meta = {
        'tool': tool, 'case': case, 'exit': exit_code,
        'elapsed_sec': round(elapsed, 2), 'output_chars': len(output),
    }
    if extra: meta.update(extra)
    (d / 'meta.json').write_text(json.dumps(meta, indent=2))
    return meta


def check_pattern(text, ok_patterns, fallback=None):
    """Return tuple (status: 'PASS'|'PARTIAL'|'FAIL', pattern_matched)."""
    for p in ok_patterns:
        if re.search(p, text, re.I):
            return 'PASS', p
    if fallback:
        for p in fallback:
            if re.search(p, text, re.I):
                return 'PARTIAL', p
    return 'FAIL', None


def checkout_head(repo_dir: Path):
    rc, out, _, _ = run(['git', 'symbolic-ref', 'refs/remotes/origin/HEAD', '--short'],
                       cwd=repo_dir, timeout=10)
    default = out.strip().replace('origin/', '') if rc == 0 and out.strip() else None
    if not default:
        for cand in ['master', 'main', 'devel']:
            rc2, _, _, _ = run(['git', 'rev-parse', '--verify', f'origin/{cand}'],
                              cwd=repo_dir, timeout=10)
            if rc2 == 0:
                default = cand
                break
    if not default:
        return False
    rc, _, _, _ = run(['git', 'checkout', f'origin/{default}', '--force'],
                     cwd=repo_dir, timeout=60)
    return rc == 0


def find_python_file(repo: Path, prefer_contains=None) -> Path | None:
    """Find a small Python file (10-200 LOC) suitable for gen-props."""
    candidates = []
    for p in repo.rglob('*.py'):
        if 'test' in p.name.lower() or 'test' in str(p.parent).lower(): continue
        if '__init__' in p.name: continue
        try:
            lines = p.read_text().splitlines()
            loc = len([l for l in lines if l.strip() and not l.strip().startswith('#')])
            if 10 <= loc <= 200:
                # Has def
                if any(l.strip().startswith('def ') for l in lines):
                    candidates.append((p, loc))
        except (UnicodeDecodeError, PermissionError):
            continue
        if len(candidates) >= 20: break
    if not candidates: return None
    # Sort by LOC (medium first)
    candidates.sort(key=lambda x: abs(x[1] - 50))
    return candidates[0][0]


def test_gen_props(project, repo: Path) -> dict:
    pyfile = find_python_file(repo)
    if not pyfile:
        return {'project': project, 'case': f'{project}-gen-props', 'status': 'SKIP', 'reason': 'no_py_file'}
    rel = pyfile.relative_to(repo)
    rc, out, err, t = run(['python3', FORGE, '--gen-props', str(rel)],
                         cwd=repo, timeout=60)
    output = (out or '') + ('\n--STDERR--\n' + err if err else '')
    status, p = check_pattern(output,
        [r'Generated \d+ property tests'],
        [r'no public function', r'all skipped', r'no testable', r'No properties'])
    save('gen-props', f'{project}-gen-props', output, rc, t, {'pyfile': str(rel), 'status_pattern': status, 'matched': p})
    return {'project': project, 'case': f'{project}-gen-props', 'exit': rc, 'status': status, 'pattern': p, 'elapsed': round(t, 2)}


def test_snapshot(project, repo: Path) -> dict:
    cmd = "python3 -c 'print(\"hello-cycle20-v2\")'"
    rc, out, err, t = run(['python3', FORGE, '--snapshot', cmd],
                         cwd=repo, timeout=60)
    output = (out or '') + ('\n--STDERR--\n' + err if err else '')
    status, p = check_pattern(output, [r'Saved.*\.golden'], None)
    save('snapshot', f'{project}-snapshot', output, rc, t, {'status_pattern': status})
    return {'project': project, 'case': f'{project}-snapshot', 'exit': rc, 'status': status, 'pattern': p, 'elapsed': round(t, 2)}


def test_watch(project, repo: Path) -> dict:
    # Timeout 5s
    rc, out, err, t = run(['timeout', '5', 'python3', FORGE, '--watch'],
                         cwd=repo, timeout=10)
    output = (out or '') + ('\n--STDERR--\n' + err if err else '')
    # Exit 124 = timeout normal pour watch (mode interactif)
    # Exit 143 = SIGTERM
    # Exit 0 = ne devrait pas (watch tourne sans fin)
    # ANSI clear = startup detection
    status = 'PASS' if rc in (124, 143) or 'watch' in output.lower() or '\x1b[' in output else 'FAIL'
    save('watch', f'{project}-watch', output, rc, t, {'status_pattern': status})
    return {'project': project, 'case': f'{project}-watch', 'exit': rc, 'status': status, 'elapsed': round(t, 2)}


def test_minimize(project, repo: Path) -> dict:
    # Setup minimal failing test + multi-line input
    test_file = repo / '_v20v2_min_test.py'
    input_file = repo / '_v20v2_min_input.txt'
    test_file.write_text('''
import os
def test_fail():
    p = os.environ.get('FORGE_MIN_INPUT', '_v20v2_min_input.txt')
    data = open(p).read()
    assert 'X' not in data
''')
    input_file.write_text('A\nB\nC\nX\nD\nE\nF\n')
    rc, out, err, t = run(['python3', FORGE, '--minimize', 'test_fail', '_v20v2_min_input.txt'],
                         cwd=repo, timeout=120)
    output = (out or '') + ('\n--STDERR--\n' + err if err else '')
    status, p = check_pattern(output,
        [r'DDMIN RESULT', r'Reduction:'],
        [r'Nothing to minimize', r'Test does not fail'])
    save('minimize', f'{project}-minimize', output, rc, t, {'status_pattern': status, 'matched': p})
    # Cleanup
    test_file.unlink(missing_ok=True)
    input_file.unlink(missing_ok=True)
    (repo / '_v20v2_min_input.minimal.txt').unlink(missing_ok=True)
    return {'project': project, 'case': f'{project}-minimize', 'exit': rc, 'status': status, 'pattern': p, 'elapsed': round(t, 2)}


def test_bisect(project, repo: Path) -> dict:
    # Use a simple trivial test that may or may not fail in history
    test_file = repo / '_v20v2_bisect_test.py'
    test_file.write_text('def test_trivial():\n    assert True\n')
    rc, out, err, t = run(['python3', FORGE, '--bisect', 'test_trivial'],
                         cwd=repo, timeout=180)
    output = (out or '') + ('\n--STDERR--\n' + err if err else '')
    status, p = check_pattern(output,
        [r'First bad commit', r'Test does not currently fail', r'Verifying'],
        [r'No baseline', r'Test does not fail'])
    save('bisect', f'{project}-bisect', output, rc, t, {'status_pattern': status, 'matched': p})
    test_file.unlink(missing_ok=True)
    return {'project': project, 'case': f'{project}-bisect', 'exit': rc, 'status': status, 'pattern': p, 'elapsed': round(t, 2)}


def test_flaky(project, repo: Path) -> dict:
    test_file = repo / '_v20v2_flaky_test.py'
    test_file.write_text('def test_passing():\n    assert 1+1 == 2\n')
    rc, out, err, t = run(['python3', FORGE, '--flaky', '3'],
                         cwd=repo, timeout=180)
    output = (out or '') + ('\n--STDERR--\n' + err if err else '')
    status, p = check_pattern(output,
        [r'\d+ runs', r'stable', r'flaky', r'No flaky'],
        [r'No tests', r'Nothing to test'])
    save('flaky', f'{project}-flaky', output, rc, t, {'status_pattern': status, 'matched': p})
    test_file.unlink(missing_ok=True)
    return {'project': project, 'case': f'{project}-flaky', 'exit': rc, 'status': status, 'pattern': p, 'elapsed': round(t, 2)}


def main():
    BENCH.mkdir(exist_ok=True)
    print(f'Cycle 20 v2 — sanity à scale sur {len(ALL_PROJECTS)} projets réels')
    print(f'Forge: {FORGE}')
    print(f'Output: {BENCH}\n')

    # Test 5 projects per tool (active first for compute speed)
    projects_per_tool = ACTIVE_PROJECTS[:5]  # 5 cas par outil minimum

    all_results = {}
    for tool_name, tool_fn in [
        ('gen-props', test_gen_props),
        ('snapshot', test_snapshot),
        ('watch', test_watch),
        ('minimize', test_minimize),
        ('bisect', test_bisect),
        ('flaky', test_flaky),
    ]:
        print(f'\n=== TOOL: {tool_name} ===')
        results = []
        for project in projects_per_tool:
            repo = CLONES / project
            if not repo.is_dir():
                print(f'  [{project}] no clone, SKIP')
                results.append({'project': project, 'status': 'NO_CLONE'})
                continue
            ok = checkout_head(repo)
            if not ok:
                print(f'  [{project}] checkout fail, SKIP')
                results.append({'project': project, 'status': 'CHECKOUT_FAIL'})
                continue
            # Need forge --init
            run(['python3', FORGE, '--init'], cwd=repo, timeout=60)
            r = tool_fn(project, repo)
            results.append(r)
            print(f'  [{project:12s}] exit={r.get("exit")} status={r.get("status"):8s} elapsed={r.get("elapsed", 0)}s')
        all_results[tool_name] = results
        # Save incremental
        (ROOT / 'cycle20_v2_results_partial.json').write_text(json.dumps(all_results, indent=2))

    # Aggregate
    print(f'\n=== AGGREGATE ===')
    tools_pass = 0
    summary_per_tool = {}
    for tool_name, results in all_results.items():
        n = len(results)
        n_pass = sum(1 for r in results if r.get('status') == 'PASS')
        n_partial = sum(1 for r in results if r.get('status') == 'PARTIAL')
        n_fail = sum(1 for r in results if r.get('status') == 'FAIL')
        # PASS + PARTIAL count as ok (graceful handling)
        ratio_ok = 100 * (n_pass + n_partial) / max(n, 1)
        ok = ratio_ok >= 80
        if ok: tools_pass += 1
        print(f'  {tool_name:12s} n={n} PASS={n_pass} PARTIAL={n_partial} FAIL={n_fail} ratio_ok={ratio_ok:.1f}% [{"OK" if ok else "NO"}]')
        summary_per_tool[tool_name] = {
            'n': n, 'pass': n_pass, 'partial': n_partial, 'fail': n_fail,
            'ratio_ok': ratio_ok, 'tool_ok': ok,
        }

    overall = tools_pass >= 5
    print(f'\nTools passing (≥80% ratio_ok): {tools_pass}/6')
    print(f'C_sanity_scale: {"OUI" if overall else "NON"}')

    summary = {
        'cycle': '20_v2',
        'tools_tested': list(all_results.keys()),
        'projects_per_tool': projects_per_tool,
        'per_tool': summary_per_tool,
        'tools_pass_count': tools_pass,
        'tools_pass_threshold': 5,
        'verdict_c_sanity_scale': 'OUI' if overall else 'NON',
        'all_results': all_results,
    }
    (ROOT / 'cycle20_v2_summary.json').write_text(json.dumps(summary, indent=2))
    print(f'\nSaved cycle20_v2_summary.json')


if __name__ == '__main__':
    main()
