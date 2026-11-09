## What changed

<!-- One paragraph. If it changes behaviour, say what breaks. -->

## Invariants touched

- [ ] Prices sum to one
- [ ] Opening price equals the supplied prior
- [ ] Path independence (total cost depends only on the final state)
- [ ] Loss bound `-b * ln(min p0)`
- [ ] Numerics (overflow, underflow, non-finite results)
- [ ] NO / bundle pricing
- [ ] Fees
- [ ] None (docs, packaging, examples)

## Checks

- [ ] `python -m unittest discover -s tests -v` passes
- [ ] A new or changed test fails on the old behaviour
- [ ] No new dependency
- [ ] Regenerated `assets/` and `docs/` if the change is visual
