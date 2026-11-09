# Contributing

This is a small library with one rule, and most of the contribution guidance
follows from it.

**The state is a vector `q`, and every operation is `C(q') - C(q)`.**

If a change keeps that true, the invariants keep holding. If it doesn't, the
loss bound and path independence stop being consequences and become claims.

## Ground rules

- **Standard library only.** The package has no dependencies and should keep
  none. If something genuinely needs a dependency, open an issue first.
- **No hidden transforms.** No silent rescaling, flooring, clamping or
  defaulting of inputs. If a caller passes a probability, that is the price.
- **Tests are the specification.** A change to `lmsr/core.py` or
  `lmsr/market.py` needs a test that asserts an exact property — equality to
  `places=9`, not "roughly the same".
- **A new test must fail on the old behaviour.** Otherwise it is documentation,
  not a test.

## Development

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
python -m unittest discover -s tests -v
```

Python 3.9 or newer. The tests use `unittest`, so there is nothing else to
install.

Regenerate the figures and the demo page after changing anything visual:

```bash
python examples/make_charts.py
python examples/depth_study.py
```

Both write into `assets/`, `docs/` and `examples/`. Commit the regenerated
files with the change.

## What good looks like

- A failing case reduced to the smallest possible `Market` call.
- The invariant it breaks, named (prices, prior, path independence, loss bound,
  numerics, NO/bundle, fees).
- A test that pins the fix.
- No change in behaviour for existing calls unless the change is the point.

## Pull requests

- One concern per pull request.
- Say which invariant the change touches, if any.
- Run the test suite and mention the Python version you used.
- By contributing you agree your work is released under the MIT licence, the
  same terms as the project.

## Reporting

- Bugs and proposals: open an issue using the templates.
- Security: see [SECURITY.md](SECURITY.md). Do not open a public issue.
