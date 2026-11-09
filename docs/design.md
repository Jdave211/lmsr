# Design notes: the decisions behind the engine

Six decisions determine whether a logarithmic market scoring rule is correct.
Each is a fork in the road. This is the choice taken, the reason, the guarantee
it buys, and the test that holds it.

---

## 1. Depth is an input, not a default

**Decision.** `Market(outcomes, b, ...)`: `b` is required. There is no default,
no floor, and no clamping.

**Why.** Depth is the only parameter that decides how far a trade moves the
price. A user-facing product will pick a sensible floor for its audience, and
should. A library cannot choose a caller's experiment for them.

**Guarantee.** The depth that was asked for is the depth in force.

**Test.** `test_b_is_required`, `test_small_b_is_honoured`.

---

## 2. The amount at risk is `-b·ln(min p)`, not `b`

**Decision.** `max_loss(b, probabilities)` returns `-b * ln(min p)`.
`b_for_loss` inverts it. The familiar `b * ln(n)` is documented as the
uniform-prior case.

**Why.** Depth is not a budget. From a uniform prior the worst case is
`b * ln(n)` — 13,863 for a binary market at `b = 20,000`. From an informed
prior it is larger, because selling a longshot cheaply is a position.

**Derivation.** Loss if `k` wins is `(q_k - q0_k) - (C(q) - C(q0))`. Since
`C(q) >= q_k`, this is at most `C(q0) - q0_k = -b ln(p0_k)`. Take the worst `k`.

**Test.** `test_max_loss_is_the_prior_bound_not_b`,
`test_informed_prior_raises_the_bound`, `test_uniform_prior_gives_b_ln_n`.

---

## 3. Prices live in log space

**Decision.** Every exponential goes through `_logsumexp`, which subtracts the
maximum first. Prices are computed from log-prices.

**Why.** `math.exp` raises `OverflowError` past ~709. Since `q` grows with every
trade and `b` can be small, a busy market can get there. At the other end, a
longshot whose exponential underflows to zero has a price of exactly zero, and
the quoting formulas then divide by it.

**Guarantee.** `q/b = 10^6` produces finite prices and finite costs; a price
that is below the smallest float still has an exact logarithm.

**Test.** `test_huge_quantities_do_not_overflow`,
`test_log_prices_survive_underflow`.

---

## 4. The prior is the price

**Decision.** `Market(..., probabilities=[0.001, 0.999])` opens at exactly
that, to twelve decimal places. Nothing is rescaled, floored, or blended.

**Why.** A research engine that quietly adjusts its inputs cannot tell you what
it traded at. Softening a longshot is a reasonable product choice; it is a
hidden transform in a library. It also silently changes the loss bound in #2,
because it caps `-ln(min p)`.

**Guarantee.** Opening prices equal the prior, and the published loss bound
describes the market that actually opened.

**Test.** `test_opening_prices_are_exactly_the_prior`,
`test_prior_is_not_softened`, `test_probabilities_are_not_silently_normalised`.

---

## 5. NO is a bundle, not a formula

**Decision.** `buy_no` buys one share of every other outcome and prices it with
`C(q + delta) - C(q)`.

**Why.** In a multi-outcome LMSR, "NO on A" is not a primitive security. It is
the bundle that pays 1 if A loses. Any bespoke complement formula bypasses the
potential, so the resulting state is not one the cost function can price — and
the loss bound no longer follows.

**Guarantee.** The closed form is

```
cost of delta NO contracts = b * ln(1 + (1 - p_i)(e^{delta/b} - 1))
```

so the per-contract price is exactly `1 - p_i` in the limit. For a binary
market it reduces to buying the other outcome.

**Test.** `test_binary_no_is_the_other_outcome`, `test_no_pays_one_per_contract`,
`test_no_cost_per_share_is_one_minus_p`,
`test_random_trades_never_break_the_bound`.

---

## 6. Path independence is a theorem, so test it

**Decision.** Sells use a closed form, and tests compare one large trade with
many small ones to nine decimal places.

**Why.** `C` is a function of `q` alone, so the total cost to reach a state
cannot depend on the path. If it does, the same final position has two prices
and someone can trade the difference. Numerical drift is where that shows up
first, and bisection is where drift hides.

**Guarantee.** Every route to the same `q` costs the same, in any order, for
bundles as well as single legs.

**Test.** `test_one_trade_equals_ten`, `test_bundle_order_does_not_matter`,
`test_sell_path_independence`, `test_shares_for_refund_inverts_sell_refund`.

---

## The rule behind all six

The state is a vector `q`, and every operation is `C(q') - C(q)`. Once that is
true, the properties stop being things to check and start being things that
cannot fail. The tests exist to prove the rule is followed, not to add
confidence.

Fees are the one deliberate exception: `fee_rate` applies to cash per trade and
therefore makes total cost path-dependent. Keep it at zero when testing
invariants.

## What is intentionally not here

- **No order book.** LMSR is a market maker; there is no matching.
- **No resolution logic.** Whether a market resolves correctly is governance,
  not pricing.
- **No persistence.** State is in memory. Storage belongs one layer up.
- **No configuration framework.** Four constructor arguments and one method per
  operation.
