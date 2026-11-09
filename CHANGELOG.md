# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] — 2026-11-09

### Added

- LMSR cost function, prices, and quoting in log space.
- `Market`: buy, sell, bundles, NO contracts, fees, and trade history.
- Closed forms for buying and selling for a cash amount; no bisection.
- Loss bound `-b * ln(min p0)`, with `b_for_loss` to invert it.
- Proper scoring rules: Brier, log loss, and calibration bins.
- Trader simulation and a depth study: accuracy against worst-case loss.
- 57 tests, most of them exact-property assertions.
- Binary and multi-outcome market cards, a static demo page, and a chart
  generator, all standard library only.

[0.1.0]: https://github.com/Jdave211/lmsr/releases/tag/v0.1.0
