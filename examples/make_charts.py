"""Generate the README charts as standalone SVG. Standard library only.

    python examples/make_charts.py

No plotting dependency, no external font, no CDN. The palette and type follow
the tenr landing page: black ground, off-white ink, grey secondary, one dashed
reference line. Everything is deterministic from a seed, so the committed SVGs
can be regenerated and diffed.
"""

from __future__ import annotations

import math
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from lmsr.core import max_loss  # noqa: E402
from lmsr.simulate import run_market  # noqa: E402

BG = "#000000"
INK = "#f7f7f7"
MUTED = "#adadad"
DIM = "#8a8a8a"
LINE = "#292929"

SERIF = "Georgia, 'Times New Roman', serif"
SANS = "ui-sans-serif, -apple-system, 'Helvetica Neue', Arial, sans-serif"
MONO = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"

B_GRID = [100, 200, 500, 1_000, 2_000, 5_000, 10_000, 20_000, 50_000]
REPS = 400
TRADERS = 30
NOISE = 0.6
BUDGET = 150.0
SKEWED_2 = [0.8, 0.2]
OPEN_2 = [0.5, 0.5]  # the market opens at equal prices; the bound is set there


# -- svg primitives ---------------------------------------------------------


def _esc(text: str) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _text(x, y, s, size=11, fill=MUTED, anchor="start", family=MONO, weight=400):
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" font-family="{family}" font-size="{size}" '
        f'fill="{fill}" text-anchor="{anchor}" font-weight="{weight}">{_esc(s)}</text>'
    )


def _line(x1, y1, x2, y2, stroke=LINE, width=1.0, dash=None):
    extra = f' stroke-dasharray="{dash}"' if dash else ""
    return (
        f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
        f'stroke="{stroke}" stroke-width="{width}"{extra}/>'
    )


def _poly(points, stroke=INK, width=2.0, dash=None):
    if not points:
        return ""
    d = "M " + " L ".join(f"{x:.2f},{y:.2f}" for x, y in points)
    extra = f' stroke-dasharray="{dash}"' if dash else ""
    return (
        f'<path d="{d}" fill="none" stroke="{stroke}" stroke-width="{width}" '
        f'stroke-linejoin="round" stroke-linecap="round"{extra}/>'
    )


def _dot(x, y, r=4.0, fill=INK):
    return f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{fill}"/>'


def _doc(width, height, label, body):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'width="{width}" height="{height}" role="img" aria-label="{_esc(label)}">\n'
        f'<rect width="{width}" height="{height}" fill="{BG}"/>\n'
        + "\n".join(body)
        + "\n</svg>\n"
    )


def _scale(v, lo, hi, a, b):
    if hi == lo:
        return a
    return a + (v - lo) / (hi - lo) * (b - a)


def _legend(items, x, y, gap=150):
    out = []
    for i, (label, stroke, width, dash) in enumerate(items):
        cx = x + i * gap
        out.append(_line(cx, y - 3, cx + 18, y - 3, stroke, width, dash))
        out.append(_text(cx + 24, y, label, 10.5, MUTED, family=SANS))
    return out


# -- chart 1: the same traders at two depths --------------------------------


def probability_chart(path_a, path_b, out: pathlib.Path) -> None:
    w, h = 880, 392
    left, right, top, bottom = 64, 26, 98, 92
    n = max(len(path_a), len(path_b)) - 1

    def xv(i):
        return _scale(i, 0, n, left, w - right)

    def yv(p):
        return _scale(p, 0.0, 1.0, h - bottom, top)

    body = [
        _text(24, 34, "Same traders, two depths", 17, INK, family=SERIF),
        _text(24, 52, "P(YES) after each trade · truth 80% · 30 traders, belief noise 0.6", 10.5, DIM, family=MONO),
    ]

    for tick in (0.0, 0.25, 0.5, 0.75, 1.0):
        y = yv(tick)
        body.append(_line(left, y, w - right, y, LINE, 0.8))
        body.append(_text(left - 10, y + 3.5, f"{tick:.2f}", 10, DIM, "end"))

    for i in range(0, n + 1, 10):
        body.append(_text(xv(i), h - bottom + 18, str(i), 10, DIM, "middle"))

    body.append(_poly([(xv(i), yv(p)) for i, p in enumerate(path_a)], MUTED, 1.1))
    body.append(_poly([(xv(i), yv(p)) for i, p in enumerate(path_b)], INK, 2.0))

    ty = yv(0.8)
    body.append(_line(left, ty, w - right, ty, DIM, 1.0, "4 4"))
    body.append(_text(w - right - 4, ty - 7, "truth 80%", 10, DIM, "end", SANS))

    body += _legend(
        [
            ("b = 2,000  (deep)", INK, 2.0, None),
            ("b = 200  (shallow)", MUTED, 1.1, None),
            ("truth", DIM, 1.0, "4 4"),
        ],
        left, h - 24, 190,
    )
    out.write_text(_doc(w, h, "Probability path in the same binary market at two depths", body))


# -- chart 2: what accuracy costs -------------------------------------------


def _series():
    rows = []
    for b in B_GRID:
        vals = [
            run_market(SKEWED_2, b, traders=TRADERS, noise=NOISE, budget=BUDGET, seed=1_000 + b + r)
            for r in range(REPS)
        ]
        rows.append(
            {
                "b": b,
                "loss": max_loss(b, OPEN_2),
                "brier": sum(v["brier"] for v in vals) / len(vals),
            }
        )
    return rows


def depth_chart(fixed, out: pathlib.Path) -> None:
    w, h = 880, 392
    left, right, top, bottom = 64, 30, 112, 84
    lo, hi = 60.0, 45_000.0
    ylo, yhi = 0.28, 0.68

    def xv(v):
        return _scale(math.log10(v), math.log10(lo), math.log10(hi), left, w - right)

    def yv(v):
        return _scale(v, ylo, yhi, h - bottom, top)

    body = [
        _text(24, 34, "What accuracy costs", 17, INK, family=SERIF),
        _text(
            24, 52,
            "Binary market, truth 80/20, opening at 50/50 · 400 replications per point",
            10.5, DIM, family=MONO,
        ),
        _text(24, 76, "expected Brier score (lower is better)", 10, DIM, family=SANS),
    ]

    for tick in (0.30, 0.40, 0.50, 0.60):
        y = yv(tick)
        body.append(_line(left, y, w - right, y, LINE, 0.8))
        body.append(_text(left - 10, y + 3.5, f"{tick:.2f}", 10, DIM, "end"))

    for tick in (100, 1_000, 10_000):
        x = xv(tick)
        body.append(_line(x, h - bottom, x, h - bottom + 5, LINE, 0.8))
        label = f"{tick // 1000}k" if tick >= 1_000 else str(tick)
        body.append(_text(x, h - bottom + 18, label, 10, DIM, "middle"))
    body.append(
        _text((left + w - right) / 2, h - bottom + 42, "worst-case maker loss (log scale)", 10, DIM, "middle")
    )

    body.append(_poly([(xv(r["loss"]), yv(r["brier"])) for r in fixed], INK, 2.0))

    best = min(fixed, key=lambda r: r["brier"])
    bx, by = xv(best["loss"]), yv(best["brier"])
    body.append(_dot(bx, by, 4.5, INK))
    body.append(_text(bx + 11, by + 22, f"b = {best['b']:,}", 10, INK, family=SANS))
    body.append(_text(bx + 11, by + 36, "best accuracy here", 9.5, DIM, family=SANS))

    out.write_text(_doc(w, h, "Accuracy against worst-case maker loss", body))


def main() -> None:
    assets = HERE.parent / "assets"
    assets.mkdir(exist_ok=True)

    shallow = run_market(SKEWED_2, 200, traders=TRADERS, noise=NOISE, budget=BUDGET, seed=7)
    deep = run_market(SKEWED_2, 2_000, traders=TRADERS, noise=NOISE, budget=BUDGET, seed=7)
    probability_chart(
        [p[0] for p in shallow["path"]],
        [p[0] for p in deep["path"]],
        assets / "probability-path.svg",
    )

    depth_chart(_series(), assets / "depth-frontier.svg")

    for name in ("probability-path.svg", "depth-frontier.svg"):
        size = (assets / name).stat().st_size
        print(f"wrote assets/{name}  ({size:,} bytes)")


if __name__ == "__main__":
    main()
