"""How deep should a market be?

Two experiments, both cheap and both reproducible:

A. Fixed trader budget, varying depth. Shallow markets amplify noise; deep
   markets underreact. If the theory is right, error is U-shaped in b and the
   minimum is the depth that matches the traders' information.

B. Budget scaled with depth, so every trade has the same price impact. Accuracy
   is then flat in b while the maker's exposure grows. That is the price of
   accuracy: roughly linear in depth.

Run:  python examples/depth_study.py
"""

from __future__ import annotations

import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from lmsr.core import max_loss  # noqa: E402
from lmsr.simulate import run_market  # noqa: E402

B_GRID = [100, 200, 500, 1_000, 2_000, 5_000, 10_000, 20_000, 50_000]
REPS = 400
TRADERS = 30
NOISE = 0.6
BUDGET = 150.0

UNIFORM_2 = [0.5, 0.5]
SKEWED_2 = [0.8, 0.2]
SKEWED_5 = [0.40, 0.25, 0.15, 0.12, 0.08]


def average(truth, b, budget, seed):
    rows = [
        run_market(truth, b, traders=TRADERS, noise=NOISE, budget=budget, seed=seed + r)
        for r in range(REPS)
    ]
    n = len(rows)
    return {
        "brier": sum(r["brier"] for r in rows) / n,
        "error": sum(r["max_abs_error"] for r in rows) / n,
        "loss": sum(r["worst_case_loss"] for r in rows) / n,
        "cap": rows[0]["max_loss"],
        "volume": sum(r["volume"] for r in rows) / n,
    }


def table(title, truth, budget_fn):
    lines = [
        f"### {title}",
        "",
        "| b | max loss | expected Brier | mean abs error | loss used | volume |",
        "|---:|---:|---:|---:|---:|---:|",
    ]
    best = None
    for b in B_GRID:
        budget = budget_fn(b, truth)
        r = average(truth, b, budget, seed=1_000 + b)
        used = r["loss"] / r["cap"] if r["cap"] else 0.0
        lines.append(
            f"| {b:,} | {r['cap']:,.0f} | {r['brier']:.4f} | "
            f"{r['error']:.4f} | {used:5.1%} | {r['volume']:,.0f} |"
        )
        if best is None or r["brier"] < best[1]:
            best = (b, r["brier"])
    lines += ["", f"Best depth in this grid: **b = {best[0]:,}** (Brier {best[1]:.4f}).", ""]
    return lines


def main() -> None:
    out = [
        "# Depth study",
        "",
        f"{REPS} replications per cell, {TRADERS} traders, belief noise {NOISE}.",
        "",
        "## A. Fixed trader budget",
        "",
        f"Each trader spends {BUDGET:,.0f}. Depth alone changes how far that moves "
        "the price. Too shallow amplifies noise, too deep underreacts.",
        "",
    ]
    out += table("Binary, truth 50/50", UNIFORM_2, lambda b, t: BUDGET)
    out += table("Binary, truth 80/20 (prior is wrong)", SKEWED_2, lambda b, t: BUDGET)
    out += table("Five outcomes, skewed truth", SKEWED_5, lambda b, t: BUDGET)

    out += [
        "## B. Depth-scaled budget (constant price impact)",
        "",
        "Each trader spends 1/40 of the maker's capacity, so the price impact per "
        "trade is roughly constant. Accuracy is then flat while exposure grows.",
        "",
    ]
    out += table("Binary, capacity-scaled budget", UNIFORM_2, lambda b, t: max_loss(b, t) / 40)
    out += table("Binary 80/20, capacity-scaled budget", SKEWED_2, lambda b, t: max_loss(b, t) / 40)
    out += table("Five outcomes, capacity-scaled budget", SKEWED_5, lambda b, t: max_loss(b, t) / 40)

    out += [
        "## Read this",
        "",
        "- **The classical `b * ln(n)` figure is a uniform-prior special case.** With an",
        "  informed prior the maker's bound is `-b * ln(min p)`, which is larger.",
        "- **Depth is a price, not a quality setting.** When the prior is right "
        "(50/50) deeper is only less noise. When the prior is wrong, panel A shows an\n"
        "  interior optimum: price impact has to match the traders' information, and\n"
        "  past that point depth just buys underreaction. In panel B accuracy is\n"
        "  roughly flat in `b` while exposure grows, so deeper is strictly more\n"
        "  expensive for the same result.",
        "- **This is a simulation.** It says how the mechanism behaves, not how a",
        "  particular market will. That distinction is the whole point of the kit.",
        "",
    ]

    text = "\n".join(out)
    (HERE / "depth_results.md").write_text(text)
    print(text)


if __name__ == "__main__":
    main()
