# Security policy

## Supported versions

The current release line, `0.1.x`, receives fixes.

## Reporting a vulnerability

Please report privately through GitHub's security advisories:

https://github.com/Jdave211/lmsr/security/advisories/new

Do not open a public issue for a vulnerability. You should get a response
within a few days.

## Scope

The interesting failures in this library are mathematical, not remote:

- a price vector that does not sum to one,
- an opening price that differs from the supplied prior,
- a trade sequence whose total cost depends on the order of trades,
- a realised loss above `-b * ln(min p0)`,
- a quoting path that overflows, underflows, or returns a non-finite number,
- a NO or bundle trade that bypasses the cost function.

If you find one, include the exact `Market` calls, the numbers, and the
invariant you expected to hold.

The demo page under `docs/` is static HTML with no network access and no user
input; issues there are ordinary bugs.
