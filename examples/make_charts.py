"""Generate the market cards and the depth chart as standalone SVG.

    python examples/make_charts.py

Standard library only. The cards are product-facing; the depth chart is
research-facing, so only the latter draws a "truth" reference. A market chart
that shows the future is not a market chart.

Contracts are illustrative. Prices come from the engine's simulation, not from
a live venue, and every card says so.
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

# A monotone ramp for stacked bands. The leader is brightest.
BANDS = ["#f0f0f0", "#c9c9c9", "#a2a2a2", "#7d7d7d", "#5c5c5c", "#414141"]

BINARY = {
    "eyebrow": "LMSR  ·  BINARY CONTRACT  ·  SIMULATED",
    "question": "Will Nvidia beat consensus EPS this quarter?",
    "outcomes": ("YES", "NO"),
    "truth": [0.62, 0.38],
    "b": 2_000,
    "traders": 30,
    "noise": 0.6,
    "budget": 150.0,
    "seed": 7,
    "resolves": "19 Nov 2026",
}

MULTI = {
    "eyebrow": "LMSR  ·  MULTI-OUTCOME  ·  SIMULATED",
    "question": "Which lab has the best model on 31 Dec 2026?",
    "outcomes": ("OpenAI", "Anthropic", "Google", "Meta", "DeepSeek", "Other"),
    "truth": [0.34, 0.24, 0.16, 0.11, 0.09, 0.06],
    "b": 6_000,
    "traders": 45,
    "noise": 0.45,
    "budget": 250.0,
    "seed": 11,
    "resolves": "31 Dec 2026",
}

B_GRID = [100, 200, 500, 1_000, 2_000, 5_000, 10_000, 20_000, 50_000]
REPS = 400
DEPTH_TRADERS = 30
DEPTH_NOISE = 0.6
DEPTH_BUDGET = 150.0
DEPTH_TRUTH = [0.8, 0.2]
DEPTH_OPEN = [0.5, 0.5]


# -- svg primitives ---------------------------------------------------------


def _esc(text: str) -> str:
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


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


def _polygon(points, fill):
    d = "M " + " L ".join(f"{x:.2f},{y:.2f}" for x, y in points) + " Z"
    return f'<path d="{d}" fill="{fill}" stroke="{BG}" stroke-width="1"/>'


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


def _pct(v: float) -> str:
    return f"{v * 100:.1f}%"


# -- binary card ------------------------------------------------------------


def binary_card(r: dict, spec: dict, out: pathlib.Path) -> str:
    yes = [p[0] for p in r["path"]]
    no = [1.0 - y for y in yes]
    n = max(len(yes) - 1, 1)
    delta = yes[-1] - 0.5

    w, h = 880, 468
    left, right, top, bottom = 58, 800, 156, 372

    def xv(i):
        return _scale(i, 0, n, left, right)

    def yv(p):
        return _scale(p, 0.0, 1.0, bottom, top)

    body = [
        f'<rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="2" fill="none" stroke="{LINE}"/>',
        _text(32, 38, spec["eyebrow"], 9.5, DIM, spacing=1.6),
        _text(32, 72, spec["question"], 24, INK, family=SERIF),
        _dot(35, 100, 3.2, INK),
        _text(46, 104, f"YES {_pct(yes[-1])}", 12.5, INK, family=SANS),
        _dot(160, 100, 3.2, MUTED),
        _text(171, 104, f"NO {_pct(no[-1])}", 12.5, MUTED, family=SANS),
        _text(
            32, 126,
            f"{'+' if delta >= 0 else ''}{delta * 100:.1f} pts since open   ·   resolves {spec['resolves']}",
            10, DIM, family=MONO,
        ),
    ]

    for tick in (0.25, 0.5, 0.75):
        y = yv(tick)
        body.append(_line(left, y, right, y, LINE, 0.8))
        body.append(_text(left - 10, y + 3.5, f"{tick * 100:.0f}%", 10, DIM, "end"))
    body.append(_line(left, bottom, right, bottom, LINE, 0.8))

    body.append(_poly([(xv(i), yv(p)) for i, p in enumerate(no)], MUTED, 1.4))
    body.append(_poly([(xv(i), yv(p)) for i, p in enumerate(yes)], INK, 2.2))

    for i in range(0, n + 1, 10):
        body.append(_text(xv(i), bottom + 20, str(i), 10, DIM, "middle"))

    body.append(_dot(right, yv(yes[-1]), 4.0, INK))
    body.append(_text(right + 12, yv(yes[-1]) + 4, f"{yes[-1] * 100:.0f}%", 11, INK, family=SANS))
    body.append(_dot(right, yv(no[-1]), 4.0, MUTED))
    body.append(_text(right + 12, yv(no[-1]) + 4, f"{no[-1] * 100:.0f}%", 11, MUTED, family=SANS))

    body.append(_line(32, 414, w - 32, 414, LINE, 0.8))
    body.append(
        _text(32, 438, f"b = {spec['b']:,}   ·   {n} trades   ·   worst-case loss {r['max_loss']:,.0f}",
              10.5, MUTED)
    )

    svg = _doc(w, h, f"Binary contract: {spec['question']}", body)
    out.write_text(svg)
    return svg


# -- multi-outcome card -----------------------------------------------------


def multi_card(r: dict, spec: dict, out: pathlib.Path) -> str:
    names = spec["outcomes"]
    path = r["path"]
    n = max(len(path) - 1, 1)
    k = len(names)
    final = path[-1]

    w, h = 880, 500
    left, right, top, bottom = 58, 606, 156, 400
    lx = 636

    def xv(i):
        return _scale(i, 0, n, left, right)

    def yv(v):
        return _scale(v, 0.0, 1.0, bottom, top)

    stacks = []
    for probs in path:
        c = 0.0
        row = []
        for v in probs:
            row.append((c, c + v))
            c += v
        stacks.append(row)

    body = [
        f'<rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="2" fill="none" stroke="{LINE}"/>',
        _text(32, 38, spec["eyebrow"], 9.5, DIM, spacing=1.6),
        _text(32, 72, spec["question"], 24, INK, family=SERIF),
        _text(
            32, 98,
            f"{k} outcomes   ·   probabilities sum to 1   ·   resolves {spec['resolves']}",
            10, DIM, family=MONO,
        ),
    ]

    for tick in (0.0, 0.5, 1.0):
        y = yv(tick)
        body.append(_line(left, y, right, y, LINE, 0.9))
        body.append(_text(left - 10, y + 3.5, f"{tick * 100:.0f}%", 10, DIM, "end"))

    for i in range(k - 1, -1, -1):
        pts = [(xv(t), yv(stacks[t][i][1])) for t in range(len(path))]
        pts += [(xv(t), yv(stacks[t][i][0])) for t in range(len(path) - 1, -1, -1)]
        body.append(_polygon(pts, BANDS[i % len(BANDS)]))

    for i in range(0, n + 1, 15):
        body.append(_text(xv(i), bottom + 20, str(i), 10, DIM, "middle"))

    body.append(_line(32, 446, w - 32, 446, LINE, 0.8))
    body.append(
        _text(32, 470, f"b = {spec['b']:,}   ·   {n} trades   ·   worst-case loss {r['max_loss']:,.0f}",
              10.5, MUTED)
    )

    for i, name in enumerate(names):
        y = 166 + i * 32
        body.append(f'<rect x="{lx}" y="{y - 10}" width="10" height="10" rx="1" fill="{BANDS[i]}"/>')
        body.append(_text(lx + 18, y, name, 11.5, INK, family=SANS))
        body.append(_text(848, y, _pct(final[i]), 11, MUTED, "end"))

    svg = _doc(w, h, f"Multi-outcome contract: {spec['question']}", body)
    out.write_text(svg)
    return svg


# -- research chart: what accuracy costs ------------------------------------


def _series():
    rows = []
    for b in B_GRID:
        vals = [
            run_market(DEPTH_TRUTH, b, traders=DEPTH_TRADERS, noise=DEPTH_NOISE,
                       budget=DEPTH_BUDGET, seed=1_000 + b + r)
            for r in range(REPS)
        ]
        rows.append(
            {
                "b": b,
                "loss": max_loss(b, DEPTH_OPEN),
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
            10.5, DIM,
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


# -- demo page --------------------------------------------------------------

DEMO = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>lmsr — markets</title>
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
  .note { margin: 26px 0 0; max-width: 62ch; color: #8a8a8a;
    font: 400 12px/1.7 ui-monospace, SFMono-Regular, Menlo, monospace; }
  h2 { margin: 52px 0 14px; font: 400 20px/1.2 Georgia, serif; letter-spacing: -.02em; }
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
  <p class="note">Illustrative contracts. Prices are simulated by the engine
  from noisy trader beliefs; they are not live quotes and carry no forecast.</p>

  <h2>Binary</h2>
  <div class="card">
$binary_svg
  </div>
  <div class="rows">
    <div class="row"><span class="k"><i class="dot yes"></i>Yes</span><span class="v">$yes%</span></div>
    <div class="row"><span class="k"><i class="dot no"></i>No</span><span class="v">$no%</span></div>
  </div>

  <h2>Multi-outcome</h2>
  <div class="card">
$multi_svg
  </div>

  <footer>Static demo. Prices generated by <code>lmsr/</code>; no build step, no
  external assets. Regenerate with <code>python examples/make_charts.py</code>.</footer>
</main>
</body>
</html>
"""


def write_demo(binary_svg: str, multi_svg: str, binary: dict, path: pathlib.Path) -> None:
    yes = binary["prices"][0]
    path.write_text(
        Template(DEMO).substitute(
            binary_svg=binary_svg.rstrip(),
            multi_svg=multi_svg.rstrip(),
            yes=f"{yes * 100:.0f}",
            no=f"{(1 - yes) * 100:.0f}",
        )
    )


def main() -> None:
    assets = HERE.parent / "assets"
    assets.mkdir(exist_ok=True)
    docs = HERE.parent / "docs"
    docs.mkdir(exist_ok=True)

    binary = run_market(
        BINARY["truth"], BINARY["b"], traders=BINARY["traders"],
        noise=BINARY["noise"], budget=BINARY["budget"], seed=BINARY["seed"],
    )
    multi = run_market(
        MULTI["truth"], MULTI["b"], traders=MULTI["traders"],
        noise=MULTI["noise"], budget=MULTI["budget"], seed=MULTI["seed"],
    )

    binary_svg = binary_card(binary, BINARY, assets / "market-binary.svg")
    multi_svg = multi_card(multi, MULTI, assets / "market-multi.svg")
    write_demo(binary_svg, multi_svg, binary, docs / "index.html")

    depth_chart(_series(), assets / "depth-frontier.svg")

    for name in ("assets/market-binary.svg", "assets/market-multi.svg",
                 "assets/depth-frontier.svg", "docs/index.html"):
        size = (HERE.parent / name).stat().st_size
        print(f"wrote {name}  ({size:,} bytes)")


if __name__ == "__main__":
    main()
