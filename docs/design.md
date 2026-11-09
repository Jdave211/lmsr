# Design notes: what changed when the engine left the product

`probable.fun` is a real product: a private-group prediction market with auth,
a database, an oracle and a browser. The LMSR engine inside it works. The notes
below are not a bug list — they are the decisions that had to be made again once
the mechanism became a library that other people would read, test and reuse.

Each section says what the product does, why a library needs it different, and
which test pins the new behaviour.

---

## 1. Depth was floored, so it could not be set

**In the product**

```python
liquidity = max(float(payload.initialLiquidity or 0), default_event_liquidity(len(outcomes)))
```

`default_event_liquidity` returns 20,000 for a binary market and grows with the
outcome count. The request field accepts values down to 2,000, but `max()` means
anything below the default is raised to it. A creator could make a market
deeper; they could not make it shallower.

**Why a library needs it different.** Depth is the only knob that decides how
far a trade moves the price. A product can pick a sensible floor for its users;
a library cannot pick one for a caller who is running an experiment.

**What this does.** `Market(outcomes, b, ...)`: `b` is a required positional
argument. There is no default because there is no correct default — the depth is
a statement about how much the maker is willing to lose.

**Test.** `test_b_is_required`, `test_small_b_is_honoured`.

---

## 2. `b` was presented as the amount at risk

**In the product.** The field is called `initialLiquidity`, is displayed as
"liquidity", and is stored as `liquidity_b`. Choosing 20,000 reasonably reads as
"I am putting up 20,000".

**Why a library needs it different.** The worst case is not `b`. For a uniform
prior it is `b * ln(n)`: about 13,863 for a binary market at `b = 20,000`. For an
informed prior it is larger still. A product can use one word loosely; a library
that reports risk cannot.

**What this does.** `max_loss(b, probabilities)` returns `-b * ln(min p)`.
`b_for_loss` inverts it. The classic `b ln n` is documented as the uniform-prior
special case, not the definition.

**Derivation.** Loss if `k` wins is `(q_k - q0_k) - (C(q) - C(q0))`. Since
`C(q) >= q_k`, this is at most `C(q0) - q0_k = -b ln(p0_k)`. Take the worst `k`.

**Test.** `test_max_loss_is_the_prior_bound_not_b`,
`test_informed_prior_raises_the_bound`, `test_uniform_prior_gives_b_ln_n`.

---

## 3. `exp(q/b)` could overflow, and longshots underflowed to zero

**In the product**

```python
sum_exp = sum(math.exp(float(item["quantity"]) / b) for item in active_outcomes(outcomes))
```

**Why a library needs it different.** `math.exp` raises `OverflowError` once its
argument passes ~709. Because `q` grows with every trade and `b` can be small, a
busy market can get there. At the other end, a longshot whose `exp` underflows to
0 has a price of exactly 0: the quoting formulas then divide by it, and the
outcome cannot be traded. `clamp_price` only affects the display.

**What this does.** Every `exp` goes through `_logsumexp`, which subtracts the
maximum first. Prices are computed from log-prices, so `log_prices` stays exact
even where the price itself is below the smallest float.

**Test.** `test_huge_quantities_do_not_overflow`,
`test_log_prices_survive_underflow`.

---

## 4. The opening price was not the price you asked for

**In the product.** `normalize_probability_values` floors every probability at
0.0025 (and at `0.35/n`), then `soften_odds_probabilities` blends the result
toward equal with weight 0.42–0.50.

**Why a library needs it different.** For a friendly product this is a sensible
guard: a 0.1% price makes a longshot feel impossible and punishes the first
trader. For a research engine it is a problem, because you can no longer say what
you traded at. The softening also hides the true loss bound (see #2): it is
precisely a way of capping `-ln(min p)`.

**What this does.** The prior is the price. `Market(..., probabilities=[0.001,
0.999])` opens at exactly that, to 12 decimal places. The friendly behaviour is
available as an explicit helper at the call site — and then you know you used it.

**Test.** `test_opening_prices_are_exactly_the_prior`,
`test_prior_is_not_softened`.

---

## 5. "NO" used complement arithmetic outside the cost function

**In the product.** `lmsr_complement_buy_shares` and friends construct a new
exponential sum with the excluded outcome removed and solve for a share count.
There is no `q` vector update and no derivation from the cost function.

**Why a library needs it different.** In a multi-outcome LMSR, "NO on A" is not a
primitive security. It is the bundle that buys one share of every *other*
outcome. The product's formula approximates that, and because it bypasses the
potential, the resulting state is not one the cost function can price. The
maker's loss bound no longer follows from the same argument.

**What this does.** `no_cost` and `Market.buy_no` build the bundle explicitly and
price it with `C(q + delta) - C(q)`. The result is exact, and it has a clean
closed form:

```
cost of delta NO contracts = b * ln(1 + (1 - p_i)(e^{delta/b} - 1))
```

so the per-contract price is exactly `1 - p_i` in the limit. For a binary market
it reduces to buying the other outcome, which is what NO means.

**Test.** `test_binary_no_is_the_other_outcome`, `test_no_pays_one_per_contract`,
`test_no_cost_per_share_is_one_minus_p`,
`test_random_trades_never_break_the_bound` (which includes NO trades).

---

## 6. Sells relied on bisection

**In the product.** Selling used a 60-iteration bisection
(`lmsr_complement_sell_shares_for_cash`), and nothing asserted that the result
was consistent with any other route to the same state.

**Why a library needs it different.** Path independence is *the* property of a
cost-function market maker. If it fails, the same final position has two prices
and someone can trade the difference. Bisection is exactly where floating-point
drift hides, and without a test there is no way to know it has.

**What this does.** Selling shares for cash has a closed form, so there is no
bisection:

```
delta = -b * ln(1 - (1 - e^{-cash/b}) / p_i)
```

with an explicit ceiling at `-b ln(1 - p_i)`. Ten small trades and one large
trade are compared with `assertAlmostEqual(..., places=9)`.

**Test.** `test_one_trade_equals_ten`, `test_bundle_order_does_not_matter`,
`test_sell_path_independence`, `test_shares_for_refund_inverts_sell_refund`.

---

## The design decision behind all six

The product stores outcomes as dictionaries with a `quantity` field and passes
them into free functions. That makes the state implicit and lets each function
carry its own arithmetic.

This version has one rule: **the state is a vector `q`, and every operation is
`C(q') - C(q)`.** Once that is true, the properties stop being things to check
and start being things that cannot fail. The tests exist to prove the rule is
being followed, not to add confidence.

## What is intentionally not here

- **No fees in the core.** `fee_rate` is a market-level parameter applied to
  cash, and it breaks path independence by design. Keep it at 0 when testing
  invariants.
- **No order book.** LMSR is a market maker; there is no matching.
- **No resolution logic.** Whether a market resolves correctly is a governance
  problem, not a pricing one.
- **No persistence.** State is in memory. The ledger belongs one layer up.
