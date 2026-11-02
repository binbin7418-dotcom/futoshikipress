#!/usr/bin/env python3
"""FutoshikiPress acceptance test.

Seeded-proof method: build a real book (2 puzzles of each difficulty,
sizes following difficulty 5/6/7), then verify every puzzle with a
solution counter written independently of the engine's (a plain
cell-by-cell backtracker with no shared code): each puzzle must have
exactly one solution and it must equal the printed solution grid.
Also: sign-consistency audit (every printed sign true of the solution),
counts, PDF geometry, determinism, and generation timing.
"""
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from futoshiki_press import run_futoshikipress  # noqa: E402

OUT = os.path.join(os.path.dirname(__file__), "out")
results = []

def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name} {detail}")

def count_solutions_plain(givens, hs, vs, limit=2):
    """Independent checker: naive backtracking, row-major, no propagation
    tricks beyond direct constraint tests. Shares no code with engine."""
    n = len(givens)
    g = [row[:] for row in givens]
    sols = []

    def ok(r, c, v):
        for i in range(n):
            if g[r][i] == v or g[i][c] == v:
                return False
        if c > 0 and hs[r][c - 1]:
            left = g[r][c - 1]
            if left and ((hs[r][c - 1] == "<") != (left < v)):
                return False
        if c < n - 1 and hs[r][c]:
            right = g[r][c + 1]
            if right and ((hs[r][c] == "<") != (v < right)):
                return False
        if r > 0 and vs[r - 1][c]:
            top = g[r - 1][c]
            if top and ((vs[r - 1][c] == "<") != (top < v)):
                return False
        if r < n - 1 and vs[r][c]:
            bot = g[r + 1][c]
            if bot and ((vs[r][c] == "<") != (v < bot)):
                return False
        return True

    def rec(pos):
        if len(sols) >= limit:
            return
        if pos == n * n:
            sols.append([row[:] for row in g])
            return
        r, c = divmod(pos, n)
        if g[r][c]:
            rec(pos + 1)
            return
        for v in range(1, n + 1):
            if ok(r, c, v):
                g[r][c] = v
                rec(pos + 1)
                g[r][c] = 0
                if len(sols) >= limit:
                    return

    rec(0)
    return sols

def main():
    t0 = time.time()
    s = run_futoshikipress(6, OUT, seed=42, difficulty="Mixed", size="Mixed")
    dt = time.time() - t0
    ps = s["puzzles"]
    check("counts: 6 puzzles", len(ps) == 6, f"({len(ps)})")
    check("sizes follow difficulty (5/6/7)",
          [p["n"] for p in ps] == [5, 6, 7, 5, 6, 7],
          f"({[p['n'] for p in ps]})")

    all_unique, signs_true = True, True
    for p in ps:
        sols = count_solutions_plain(p["givens"], p["hsigns"], p["vsigns"], limit=2)
        if len(sols) != 1 or sols[0] != p["solution"]:
            all_unique = False
        n = p["n"]
        for r in range(n):
            for c in range(n - 1):
                sg = p["hsigns"][r][c]
                if sg and ((sg == "<") != (p["solution"][r][c] < p["solution"][r][c + 1])):
                    signs_true = False
        for r in range(n - 1):
            for c in range(n):
                sg = p["vsigns"][r][c]
                if sg and ((sg == "<") != (p["solution"][r][c] < p["solution"][r + 1][c])):
                    signs_true = False
    check("every puzzle: exactly one solution (independent plain backtracker), "
          "equal to printed solution", all_unique, "")
    check("every printed sign is true of the solution", signs_true, "")
    dug = all(p["given_count"] < p["n"] * p["n"] for p in ps)
    check("digging actually removed givens on every puzzle", dug,
          f"(givens: {[p['given_count'] for p in ps]})")
    check("signs were dug too (not all signs printed)",
          all(p["sign_count"] < p["n"] * (p["n"] - 1) * 2 for p in ps),
          f"(signs: {[p['sign_count'] for p in ps]})")

    with open(s["pdf_path"], "rb") as fh:
        data = fh.read()
    pages = data.count(b"/Type /Page") - data.count(b"/Type /Pages")
    check("PDF 612x792pt, pages = title + 6 puzzles + solutions header + 6 solutions",
          b"612 792" in data and pages == 14, f"({pages} pages)")
    check("6-puzzle mixed book builds in under 120s", dt < 120, f"({dt:.1f}s)")

    s2 = run_futoshikipress(6, OUT, seed=42, difficulty="Mixed", size="Mixed")
    same = [p["givens"] for p in s2["puzzles"]] == [p["givens"] for p in ps]
    check("deterministic for fixed seed", same, "")

    npass = sum(1 for _, ok, _ in results if ok)
    print(f"\n{npass}/{len(results)} PASS")
    with open(os.path.join(os.path.dirname(__file__), "acceptance_results.txt"), "w") as fh:
        for name, ok, detail in results:
            fh.write(f"[{'PASS' if ok else 'FAIL'}] {name} {detail}\n")
        fh.write(f"\n{npass}/{len(results)} PASS\n")
    return 0 if npass == len(results) else 1

if __name__ == "__main__":
    sys.exit(main())
