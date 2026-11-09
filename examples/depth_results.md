# Depth study

400 replications per cell, 30 traders, belief noise 0.6.

## A. Fixed trader budget

Each trader spends 150. Depth alone changes how far that moves the price. Too shallow amplifies noise, too deep underreacts.

### Binary, truth 50/50

| b | max loss | expected Brier | mean abs error | loss used | volume |
|---:|---:|---:|---:|---:|---:|
| 100 | 69 | 0.7083 | 0.3217 | 71.6% | 4,500 |
| 200 | 139 | 0.5892 | 0.1974 | 47.2% | 4,500 |
| 500 | 347 | 0.5298 | 0.1012 | 25.7% | 4,500 |
| 1,000 | 693 | 0.5149 | 0.0697 | 18.3% | 4,500 |
| 2,000 | 1,386 | 0.5060 | 0.0442 | 12.0% | 4,500 |
| 5,000 | 3,466 | 0.5026 | 0.0289 |  8.0% | 4,500 |
| 10,000 | 6,931 | 0.5013 | 0.0199 |  5.6% | 4,500 |
| 20,000 | 13,863 | 0.5005 | 0.0128 |  3.6% | 4,500 |
| 50,000 | 34,657 | 0.5001 | 0.0059 |  1.7% | 4,500 |

Best depth in this grid: **b = 50,000** (Brier 0.5001).

### Binary, truth 80/20 (prior is wrong)

| b | max loss | expected Brier | mean abs error | loss used | volume |
|---:|---:|---:|---:|---:|---:|
| 100 | 69 | 0.6436 | 0.2955 | 73.9% | 4,500 |
| 200 | 139 | 0.4515 | 0.1999 | 52.1% | 4,500 |
| 500 | 347 | 0.3703 | 0.1246 | 46.4% | 4,500 |
| 1,000 | 693 | 0.3500 | 0.1017 | 48.6% | 4,500 |
| 2,000 | 1,386 | 0.3410 | 0.0904 | 50.3% | 4,500 |
| 5,000 | 3,466 | 0.3464 | 0.1103 | 46.3% | 4,500 |
| 10,000 | 6,931 | 0.3727 | 0.1613 | 35.3% | 4,500 |
| 20,000 | 13,863 | 0.4129 | 0.2153 | 22.6% | 4,500 |
| 50,000 | 34,657 | 0.4576 | 0.2623 | 10.5% | 4,500 |

Best depth in this grid: **b = 2,000** (Brier 0.3410).

### Five outcomes, skewed truth

| b | max loss | expected Brier | mean abs error | loss used | volume |
|---:|---:|---:|---:|---:|---:|
| 100 | 161 | 1.1302 | 0.5273 | 85.3% | 4,500 |
| 200 | 322 | 0.9193 | 0.3250 | 65.6% | 4,500 |
| 500 | 805 | 0.7892 | 0.1634 | 42.9% | 4,500 |
| 1,000 | 1,609 | 0.7584 | 0.1055 | 38.6% | 4,500 |
| 2,000 | 3,219 | 0.7473 | 0.0784 | 36.6% | 4,500 |
| 5,000 | 8,047 | 0.7424 | 0.0646 | 33.7% | 4,500 |
| 10,000 | 16,094 | 0.7477 | 0.0857 | 28.3% | 4,500 |
| 20,000 | 32,189 | 0.7621 | 0.1255 | 19.6% | 4,500 |
| 50,000 | 80,472 | 0.7805 | 0.1656 |  9.8% | 4,500 |

Best depth in this grid: **b = 5,000** (Brier 0.7424).

## B. Depth-scaled budget (constant price impact)

Each trader spends 1/40 of the maker's capacity, so the price impact per trade is roughly constant. Accuracy is then flat while exposure grows.

### Binary, capacity-scaled budget

| b | max loss | expected Brier | mean abs error | loss used | volume |
|---:|---:|---:|---:|---:|---:|
| 100 | 69 | 0.5015 | 0.0215 |  6.0% | 52 |
| 200 | 139 | 0.5015 | 0.0219 |  6.1% | 104 |
| 500 | 347 | 0.5014 | 0.0211 |  5.9% | 260 |
| 1,000 | 693 | 0.5013 | 0.0206 |  5.8% | 520 |
| 2,000 | 1,386 | 0.5013 | 0.0207 |  5.8% | 1,040 |
| 5,000 | 3,466 | 0.5015 | 0.0219 |  6.1% | 2,599 |
| 10,000 | 6,931 | 0.5015 | 0.0216 |  6.0% | 5,199 |
| 20,000 | 13,863 | 0.5016 | 0.0224 |  6.3% | 10,397 |
| 50,000 | 34,657 | 0.5015 | 0.0218 |  6.1% | 25,993 |

Best depth in this grid: **b = 1,000** (Brier 0.5013).

### Binary 80/20, capacity-scaled budget

| b | max loss | expected Brier | mean abs error | loss used | volume |
|---:|---:|---:|---:|---:|---:|
| 100 | 69 | 0.3435 | 0.1009 | 48.1% | 121 |
| 200 | 139 | 0.3430 | 0.0998 | 48.4% | 241 |
| 500 | 347 | 0.3408 | 0.0954 | 49.3% | 604 |
| 1,000 | 693 | 0.3408 | 0.0953 | 49.3% | 1,207 |
| 2,000 | 1,386 | 0.3406 | 0.0944 | 49.5% | 2,414 |
| 5,000 | 3,466 | 0.3423 | 0.0983 | 48.7% | 6,035 |
| 10,000 | 6,931 | 0.3427 | 0.0995 | 48.4% | 12,071 |
| 20,000 | 13,863 | 0.3413 | 0.0966 | 49.0% | 24,142 |
| 50,000 | 34,657 | 0.3413 | 0.0969 | 49.0% | 60,354 |

Best depth in this grid: **b = 2,000** (Brier 0.3406).

### Five outcomes, capacity-scaled budget

| b | max loss | expected Brier | mean abs error | loss used | volume |
|---:|---:|---:|---:|---:|---:|
| 100 | 161 | 0.7449 | 0.0709 | 37.0% | 189 |
| 200 | 322 | 0.7448 | 0.0704 | 37.2% | 379 |
| 500 | 805 | 0.7457 | 0.0725 | 37.3% | 947 |
| 1,000 | 1,609 | 0.7454 | 0.0716 | 37.3% | 1,894 |
| 2,000 | 3,219 | 0.7456 | 0.0736 | 36.5% | 3,789 |
| 5,000 | 8,047 | 0.7463 | 0.0766 | 35.7% | 9,471 |
| 10,000 | 16,094 | 0.7450 | 0.0713 | 37.2% | 18,943 |
| 20,000 | 32,189 | 0.7458 | 0.0736 | 36.8% | 37,886 |
| 50,000 | 80,472 | 0.7458 | 0.0740 | 36.2% | 94,715 |

Best depth in this grid: **b = 200** (Brier 0.7448).

## Read this

- **The classical `b * ln(n)` figure is a uniform-prior special case.** With an
  informed prior the maker's bound is `-b * ln(min p)`, which is larger.
- **Depth is a price, not a quality setting.** When the prior is right (50/50) deeper is only less noise. When the prior is wrong, panel A shows an
  interior optimum: price impact has to match the traders' information, and
  past that point depth just buys underreaction. In panel B accuracy is
  roughly flat in `b` while exposure grows, so deeper is strictly more
  expensive for the same result.
- **This is a simulation.** It says how the mechanism behaves, not how a
  particular market will. That distinction is the whole point of the kit.
