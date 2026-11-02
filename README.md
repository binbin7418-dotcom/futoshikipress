# FutoshikiPress

Build print-ready **Futoshiki (inequality) puzzle books for Amazon KDP** where every puzzle is *proven* to have exactly one solution.

## Why

Futoshiki looks simple — a Latin square plus inequality signs — which is exactly why the cheap generators get it wrong: deal some givens, print some signs, borrow an answer key from the grid you started with, and never check whether the printed clues actually force that answer. FutoshikiPress starts from a complete Latin square, derives every true inequality sign, then **digs givens and signs away one at a time**: a removal is kept only while an independent solver (constraint propagation + backtracking, written separately from the generator) still finds **exactly one** solution. Digging stops at the difficulty targets — Easy keeps about 45% of cells and 70% of signs, Hard digs to about 20% of cells and 40% of signs — or when nothing more can be removed without breaking uniqueness. Before the book is written, every puzzle is re-counted from its printed givens and signs alone.

## Use

**App (Windows):** launch `FutoshikiPress.exe`, choose the puzzle count, difficulty (Easy / Medium / Hard / Mixed), grid size (5/6/7 — Mixed follows difficulty: 5×5 Easy, 6×6 Medium, 7×7 Hard) and a seed, click **Build the book**. Output: `futoshiki_book.pdf` in a `futoshikipress_out` folder — title page, one puzzle per page with givens/signs counts printed, then full solutions. 8.5×11in (612×792pt).

**Command line:** `python futoshiki_press.py out/ --puzzles=100 --difficulty=Mixed --size=Mixed --seed=42`

A 6-puzzle sample book is included (`sample_book.pdf`).

## Verified

Acceptance test (9/9 PASS, `test/acceptance_results.txt`): a 6-puzzle mixed book (5×5/6×6/7×7) re-verified by a *second, deliberately naive* backtracking checker sharing no code with the engine — every puzzle exactly one solution, equal to the printed solution; every printed sign true of its solution; digging reached the per-difficulty targets on all six puzzles (givens 11/11/10 across sizes, signs dug on all); PDF exactly 14 pages at 612×792pt; whole book generated and verified in about a second; deterministic for a fixed seed.

## Scope

Classic Futoshiki on 5×5–7×7 grids. Given/sign counts are targets: digging stops at the target or at the uniqueness floor, whichever comes first — actual counts are printed on every puzzle page, never hidden. Deterministic seeds make series production repeatable. 100% local — no uploads, no accounts, no per-book fees.

## Build from source

`pip install pyinstaller reportlab`, then `pyinstaller futoshikipress.spec`. Or push to GitHub and let the included Actions workflow build the Windows package.
