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
from string import Template

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


def _text(x, y, s, size=11, fill=MUTED, anchor="start", family=MONO, weight=400, spacing=None):
    extra = f' letter-spacing="{spacing}"' if spacing is not None else ""
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" font-family="{family}" font-size="{size}" '
        f'fill="{fill}" text-anchor="{anchor}" font-weight="{weight}"{extra}>{_esc(s)}</text>'
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


# -- chart 1: the market card ------------------------------------------------


def market_card(deep, out: pathlib.Path) -> str:
    """A binary market as a card: question, live odds, both sides, risk.

    The idiom is deliberately closer to a product readout than a research plot:
    one question, two complementary lines, direct labels at the right edge, and
    the maker's worst case printed where a reader will see it.
    """
    yes = [p[0] for p in deep["path"]]
    no = [1.0 - y for y in yes]
    n = max(len(yes) - 1, 1)

    w, h = 880, 468
    left, right, top, bottom = 58, 800, 150, 372

    def xv(i):
        return _scale(i, 0, n, left, right)

    def yv(p):
        return _scale(p, 0.0, 1.0, bottom, top)

    body = [
        f'<rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="2" '
        f'fill="none" stroke="{LINE}"/>',
        _text(32, 38, "LMSR  ·  BINARY MARKET", 9.5, DIM, spacing=1.6),
        _text(32, 72, "Will it rain tomorrow?", 26, INK, family=SERIF),
    ]

    # current odds
    body.append(_dot(35, 100, 3.2, INK))
    body.append(_text(46, 104, f"YES {yes[-1] * 100:.1f}%", 12.5, INK, family=SANS))
    body.append(_dot(155, 100, 3.2, MUTED))
    body.append(_text(166, 104, f"NO {no[-1] * 100:.1f}%", 12.5, MUTED, family=SANS))

    for tick in (0.25, 0.5, 0.75):
        y = yv(tick)
        body.append(_line(left, y, right, y, LINE, 0.8))
        body.append(_text(left - 10, y + 3.5, f"{tick * 100:.0f}%", 10, DIM, "end"))
    body.append(_line(left, bottom, right, bottom, LINE, 0.8))

    body.append(_poly([(xv(i), yv(p)) for i, p in enumerate(no)], MUTED, 1.4))
    body.append(_poly([(xv(i), yv(p)) for i, p in enumerate(yes)], INK, 2.2))

    ty = yv(0.8)
    body.append(_line(left, ty, right, ty, DIM, 1.0, "4 4"))
    body.append(_text(right - 4, ty - 7, "truth 80%", 10, DIM, "end", SANS))

    for i in range(0, n + 1, 10):
        body.append(_text(xv(i), bottom + 20, str(i), 10, DIM, "middle"))

    body.append(_dot(right, yv(yes[-1]), 4.0, INK))
    body.append(_text(right + 12, yv(yes[-1]) + 4, f"{yes[-1] * 100:.0f}%", 11, INK, family=SANS))
    body.append(_dot(right, yv(no[-1]), 4.0, MUTED))
    body.append(_text(right + 12, yv(no[-1]) + 4, f"{no[-1] * 100:.0f}%", 11, MUTED, family=SANS))

    body.append(_line(32, 414, w - 32, 414, LINE, 0.8))
    body.append(
        _text(
            32, 438,
            f"b = {deep['b']:,}   ·   {n} trades   ·   truth 80%",
            10.5, MUTED, family=MONO,
        )
    )
    body.append(
        _text(w - 32, 438, f"worst-case loss {deep['max_loss']:,.0f}", 10.5, MUTED, "end", MONO)
    )

    svg = _doc(w, h, "A binary market: probability of YES and NO over thirty trades", body)
    out.write_text(svg)
    return svg


# -- chart 2: what accuracy costs -------------------------------------------


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


DEMO = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>lmsr — market</title>
<style>
  :root { color-scheme: dark; }
  * { box-sizing: border-box; }
  body { margin: 0; background: #000; color: #f7f7f7;
    font: 400 16px/1.55 ui-sans-serif, -apple-system, "Helvetica Neue", Arial, sans-serif;
    -webkit-font-smoothing: antialiased; }
  main { width: min(820px, 100% - 40px); margin: 0 auto; padding: 56px 0 88px; }
  .top { display: flex; justify-content: space-between; align-items: baseline;
    font: 400 12px/1.45 ui-monospace, SFMono-Regular, Menlo, monospace;
    color: #adadad; text-transform: uppercase; letter-spacing: .08em; }
  .top a { color: #adadad; text-decoration: none; border-bottom: 1px solid #292929; padding-bottom: 2px; }
  .card { margin-top: 22px; }
  .card svg { display: block; width: 100%; height: auto; }
  .rows { border: 1px solid #292929; border-top: 0; }
  .row { display: flex; justify-content: space-between; align-items: center;
    padding: 18px 24px; border-top: 1px solid #292929; }
  .row:first-child { border-top: 0; }
  .k { display: flex; align-items: center; gap: 10px; font-size: 15px; }
  .dot { width: 9px; height: 9px; border-radius: 50%; display: inline-block; }
  .dot.yes { background: #f7f7f7; }
  .dot.no { background: #adadad; }
  .v { font: 500 30px/1 ui-monospace, SFMono-Regular, Menlo, monospace; letter-spacing: -.02em; }
  footer { margin-top: 52px; font: 400 12px/1.7 ui-monospace, SFMono-Regular, Menlo, monospace; color: #777; }
  footer code { color: #adadad; }
  @media (max-width: 520px) { .v { font-size: 24px; } .row { padding: 15px 18px; } }
</style>
</head>
<body>
<main>
  <div class="top"><span>LMSR</span><a href="https://github.com/Jdave211/lmsr">source</a></div>
  <div class="card">
$svg
  </div>
  <div class="rows">
    <div class="row"><span class="k"><i class="dot yes"></i>Yes</span><span class="v">$yes%</span></div>
    <div class="row"><span class="k"><i class="dot no"></i>No</span><span class="v">$no%</span></div>
  </div>
  <footer>Static demo. Prices generated by the engine in <code>lmsr/</code>.
  No build step, no external assets. Regenerate with <code>python examples/make_charts.py</code>.</footer>
</main>
</body>
</html>
"""


def write_demo(svg: str, deep: dict, path: pathlib.Path) -> None:
    yes = deep["prices"][0]
    n = len(deep["path"]) - 1
    path.write_text(
        Template(DEMO).substitute(
            svg=svg.rstrip(),
            yes=f"{yes * 100:.0f}",
            no=f"{(1 - yes) * 100:.0f}",
            b=f"{int(deep['b']):,}",
            n=n,
            loss=f"{int(deep['max_loss']):,}",
        )
    )


def main() -> None:
    assets = HERE.parent / "assets"
    assets.mkdir(exist_ok=True)
    docs = HERE.parent / "docs"
    docs.mkdir(exist_ok=True)

    deep = run_market(SKEWED_2, 2_000, traders=TRADERS, noise=NOISE, budget=BUDGET, seed=7)
    svg = market_card(deep, assets / "probability-path.svg")
    write_demo(svg, deep, docs / "index.html")

    depth_chart(_series(), assets / "depth-frontier.svg")

    for name in ("assets/probability-path.svg", "assets/depth-frontier.svg", "docs/index.html"):
        size = (HERE.parent / name).stat().st_size
        print(f"wrote {name}  ({size:,} bytes)")


if __name__ == "__main__":
    main()
