#!/usr/bin/env python3
"""FutoshikiPress engine: Futoshiki (inequality) puzzle books (PDF) where
every puzzle is PROVEN to have exactly one solution.

How a puzzle is made: a complete Latin square is generated first. Every
adjacent pair implies an inequality sign. Then givens and signs are dug
away one at a time, in random order -- a removal is kept only while an
independent solution counter (constraint propagation + MRV backtracking,
written separately from the generator) still finds exactly one solution.
Digging stops at the difficulty targets or when nothing more can be
removed. Before the book is written, every puzzle is re-counted from its
printed givens and signs alone and must return exactly one solution,
identical to the generated grid.

Deterministic for a fixed seed. 100% local. Requires: reportlab.

Usage:
    python futoshiki_press.py out/ [--puzzles 20] [--size Mixed]
                              [--difficulty Mixed] [--seed 42]
"""
import os
import random
import sys

PAGE_W, PAGE_H = 612, 792
GIVEN_KEEP = {"Easy": 0.45, "Medium": 0.32, "Hard": 0.20}
SIGN_KEEP = {"Easy": 0.70, "Medium": 0.55, "Hard": 0.40}
SIZES = {"Easy": 5, "Medium": 6, "Hard": 7}

# ---------------------------------------------------------------- solver
# Signs: hsigns[r][c] in {'<','>',''} compares (r,c) with (r,c+1);
#        vsigns[r][c] in {'<','>',''} compares (r,c) with (r+1,c)
#        ('<' always reads left<right / top<bottom).

def _propagate(dom, n, hsigns, vsigns):
    """Tighten domains in place; return False on contradiction."""
    changed = True
    while changed:
        changed = False
        # alldiff: singleton values leave their row/col peers
        for r in range(n):
            for c in range(n):
                if len(dom[r][c]) == 1:
                    v = next(iter(dom[r][c]))
                    for cc in range(n):
                        if cc != c and v in dom[r][cc]:
                            dom[r][cc] = dom[r][cc] - {v}
                            if not dom[r][cc]:
                                return False
                            changed = True
                    for rr in range(n):
                        if rr != r and v in dom[rr][c]:
                            dom[rr][c] = dom[rr][c] - {v}
                            if not dom[rr][c]:
                                return False
                            changed = True
        # inequalities
        for r in range(n):
            for c in range(n - 1):
                s = hsigns[r][c]
                if not s:
                    continue
                a, b = (dom[r][c], dom[r][c + 1]) if s == "<" else (dom[r][c + 1], dom[r][c])
                na = {x for x in a if x < max(b)}
                nb = {x for x in b if x > min(a)}
                if not na or not nb:
                    return False
                if s == "<":
                    if na != dom[r][c]:
                        dom[r][c] = na; changed = True
                    if nb != dom[r][c + 1]:
                        dom[r][c + 1] = nb; changed = True
                else:
                    if nb != dom[r][c]:
                        dom[r][c] = nb; changed = True
                    if na != dom[r][c + 1]:
                        dom[r][c + 1] = na; changed = True
        for r in range(n - 1):
            for c in range(n):
                s = vsigns[r][c]
                if not s:
                    continue
                a, b = (dom[r][c], dom[r + 1][c]) if s == "<" else (dom[r + 1][c], dom[r][c])
                na = {x for x in a if x < max(b)}
                nb = {x for x in b if x > min(a)}
                if not na or not nb:
                    return False
                if s == "<":
                    if na != dom[r][c]:
                        dom[r][c] = na; changed = True
                    if nb != dom[r + 1][c]:
                        dom[r + 1][c] = nb; changed = True
                else:
                    if nb != dom[r][c]:
                        dom[r][c] = nb; changed = True
                    if na != dom[r + 1][c]:
                        dom[r + 1][c] = na; changed = True
    return True

def count_solutions(givens, hsigns, vsigns, limit=2):
    """Count solutions of a Futoshiki position. Returns (count, first)."""
    n = len(givens)
    base = [[{givens[r][c]} if givens[r][c] else set(range(1, n + 1))
             for c in range(n)] for r in range(n)]
    found = []

    def rec(dom):
        if len(found) >= limit:
            return
        dom = [[set(cell) for cell in row] for row in dom]
        if not _propagate(dom, n, hsigns, vsigns):
            return
        best, best_opts = None, None
        for r in range(n):
            for c in range(n):
                if len(dom[r][c]) > 1 and (best_opts is None or len(dom[r][c]) < len(best_opts)):
                    best, best_opts = (r, c), sorted(dom[r][c])
        if best is None:
            found.append([[next(iter(dom[r][c])) for c in range(n)] for r in range(n)])
            return
        r, c = best
        for v in best_opts:
            dom2 = [[set(cell) for cell in row] for row in dom]
            dom2[r][c] = {v}
            rec(dom2)
            if len(found) >= limit:
                return

    if _propagate([[set(cell) for cell in row] for row in base], n, hsigns, vsigns):
        rec(base)
    return len(found), (found[0] if found else None)

# -------------------------------------------------------------- generator

def fill_latin(rng, n):
    g = [[0] * n for _ in range(n)]

    def rec(pos):
        if pos == n * n:
            return True
        r, c = divmod(pos, n)
        opts = [v for v in range(1, n + 1)
                if v not in g[r] and v not in [g[i][c] for i in range(n)]]
        rng.shuffle(opts)
        for v in opts:
            g[r][c] = v
            if rec(pos + 1):
                return True
            g[r][c] = 0
        return False

    rec(0)
    return g

def signs_from_solution(sol):
    n = len(sol)
    hs = [[""] * (n - 1) for _ in range(n)]
    vs = [[""] * n for _ in range(n - 1)]
    for r in range(n):
        for c in range(n - 1):
            hs[r][c] = "<" if sol[r][c] < sol[r][c + 1] else ">"
    for r in range(n - 1):
        for c in range(n):
            vs[r][c] = "<" if sol[r][c] < sol[r + 1][c] else ">"
    return hs, vs

def make_puzzle(rng, n, difficulty):
    sol = fill_latin(rng, n)
    hs, vs = signs_from_solution(sol)
    givens = [row[:] for row in sol]
    total_signs = n * (n - 1) * 2
    given_target = max(2, int(n * n * GIVEN_KEEP[difficulty]))
    sign_target = int(total_signs * SIGN_KEEP[difficulty])
    items = ([("g", r, c) for r in range(n) for c in range(n)] +
             [("h", r, c) for r in range(n) for c in range(n - 1)] +
             [("v", r, c) for r in range(n - 1) for c in range(n)])
    rng.shuffle(items)
    gcount, scount = n * n, total_signs
    for kind, r, c in items:
        if kind == "g" and gcount <= given_target:
            continue
        if kind in "hv" and scount <= sign_target:
            continue
        if kind == "g":
            old, givens[r][c] = givens[r][c], 0
        elif kind == "h":
            old, hs[r][c] = hs[r][c], ""
        else:
            old, vs[r][c] = vs[r][c], ""
        cnt, _ = count_solutions(givens, hs, vs, limit=2)
        if cnt == 1:
            if kind == "g":
                gcount -= 1
            else:
                scount -= 1
        else:
            if kind == "g":
                givens[r][c] = old
            elif kind == "h":
                hs[r][c] = old
            else:
                vs[r][c] = old
    cnt, found = count_solutions(givens, hs, vs, limit=2)
    if cnt != 1 or found != sol:
        raise RuntimeError("internal: dug puzzle failed final proof")
    return {"n": n, "givens": givens, "hsigns": hs, "vsigns": vs,
            "solution": sol, "given_count": gcount, "sign_count": scount,
            "difficulty": difficulty}

# -------------------------------------------------------------------- PDF

def _draw_grid(c, p, x0, y_top, cell, solved=False):
    from reportlab.lib.colors import HexColor
    ink = HexColor("#1a1a1a")
    grid_col = HexColor("#444444")
    n = p["n"]
    grid = p["solution"] if solved else p["givens"]
    c.setStrokeColor(grid_col)
    c.setLineWidth(1.1)
    for i in range(n + 1):
        c.line(x0, y_top - i * cell, x0 + n * cell, y_top - i * cell)
        c.line(x0 + i * cell, y_top, x0 + i * cell, y_top - n * cell)
    c.setFillColor(ink)
    for r in range(n):
        for cc in range(n):
            v = grid[r][cc]
            if v:
                c.setFont("Helvetica-Bold" if not solved else "Helvetica", cell * 0.44)
                c.drawCentredString(x0 + cc * cell + cell / 2,
                                    y_top - r * cell - cell * 0.64, str(v))
    if not solved:
        c.setFont("Helvetica-Bold", cell * 0.36)
        for r in range(n):
            for cc in range(n - 1):
                s = p["hsigns"][r][cc]
                if s:
                    c.drawCentredString(x0 + (cc + 1) * cell,
                                        y_top - r * cell - cell * 0.63, s)
        for r in range(n - 1):
            for cc in range(n):
                s = p["vsigns"][r][cc]
                if s:
                    # point of the sign faces the smaller cell:
                    # top<bottom -> caret (point up); top>bottom -> vee
                    glyph = "^" if s == "<" else "v"
                    c.drawCentredString(x0 + cc * cell + cell / 2,
                                        y_top - (r + 1) * cell - cell * 0.14, glyph)

def render_pdf(path, puzzles):
    from reportlab.pdfgen import canvas as rl_canvas
    from reportlab.lib.colors import HexColor
    ink = HexColor("#1a1a1a")
    accent = HexColor("#2050a0")
    c = rl_canvas.Canvas(path, pagesize=(PAGE_W, PAGE_H))
    c.setFillColor(ink)
    c.setFont("Helvetica-Bold", 30)
    c.drawString(72, 640, "FutoshikiPress")
    c.setFont("Helvetica", 15)
    c.drawString(72, 606, "Inequality puzzle books with proven unique solutions.")
    c.setFont("Helvetica", 11.5)
    lines = [
        "Fill the grid so every row and column holds 1..N once, obeying",
        "every inequality sign between neighbours. Each puzzle here was",
        "dug from a complete Latin square -- givens and signs removed one",
        "at a time, kept only while a separate solver still found",
        "exactly one solution.",
        "",
        f"{len(puzzles)} puzzles with full solutions at the back.",
    ]
    y = 540
    for ln in lines:
        c.drawString(72, y, ln)
        y -= 20
    c.showPage()
    for i, p in enumerate(puzzles, 1):
        n = p["n"]
        cell = min(76, 430 // n)
        x0 = (PAGE_W - n * cell) // 2
        c.setFillColor(ink)
        c.setFont("Helvetica-Bold", 15)
        c.drawString(54, 748, f"Puzzle {i} -- {p['difficulty']} ({n}x{n})")
        c.setFont("Helvetica", 10.5)
        c.setFillColor(accent)
        c.drawString(54, 730, f"{p['given_count']} givens, {p['sign_count']} inequality signs -- one solution, proven")
        _draw_grid(c, p, x0, 700, cell)
        c.showPage()
    c.setFont("Helvetica-Bold", 16)
    c.setFillColor(ink)
    c.drawString(54, 748, "Solutions")
    c.showPage()
    for i, p in enumerate(puzzles, 1):
        n = p["n"]
        cell = min(60, 430 // n)
        x0 = (PAGE_W - n * cell) // 2
        c.setFillColor(ink)
        c.setFont("Helvetica-Bold", 13)
        c.drawString(54, 748, f"Solution {i}")
        _draw_grid(c, p, x0, 716, cell, solved=True)
        c.showPage()
    c.save()
    with open(path, "rb") as fh:
        data = fh.read()
    return data.count(b"/Type /Page") - data.count(b"/Type /Pages")

# -------------------------------------------------------------------- run

def run_futoshikipress(count, outdir, seed=42, difficulty="Mixed", size="Mixed", **kw):
    if difficulty not in ("Easy", "Medium", "Hard", "Mixed"):
        raise ValueError("difficulty must be Easy, Medium, Hard or Mixed")
    if size not in ("5", "6", "7", "Mixed"):
        raise ValueError("size must be 5, 6, 7 or Mixed")
    os.makedirs(outdir, exist_ok=True)
    rng = random.Random(seed)
    puzzles = []
    diffs = ["Easy", "Medium", "Hard"]
    for i in range(count):
        d = diffs[i % 3] if difficulty == "Mixed" else difficulty
        n = SIZES[d] if size == "Mixed" else int(size)
        puzzles.append(make_puzzle(rng, n, d))
    pdf_path = os.path.join(outdir, "futoshiki_book.pdf")
    pages = render_pdf(pdf_path, puzzles)
    return {"puzzles": puzzles, "pages": pages, "pdf_path": pdf_path,
            "count": len(puzzles)}

def main(argv):
    outdir = argv[1] if len(argv) > 1 else "out"
    opts = {"puzzles": 20, "difficulty": "Mixed", "size": "Mixed", "seed": 42}
    for a in argv[2:]:
        if a.startswith("--") and "=" in a:
            k, v = a[2:].split("=", 1)
            if k in ("puzzles", "seed"):
                v = int(v)
            opts[k] = v
    s = run_futoshikipress(opts["puzzles"], outdir, seed=opts["seed"],
                           difficulty=opts["difficulty"], size=opts["size"])
    for i, p in enumerate(s["puzzles"], 1):
        print(f"Puzzle {i}: {p['difficulty']} {p['n']}x{p['n']}, "
              f"{p['given_count']} givens, {p['sign_count']} signs, unique solution proven")
    print(f"Pages: {s['pages']}")
    print(f"PDF: {s['pdf_path']}")
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv))
