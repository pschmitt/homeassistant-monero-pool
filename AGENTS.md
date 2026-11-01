# Agent instructions

## Project

This Home Assistant integration reports Monero mining statistics from Hashvault wallet data or an XMRig proxy, including aggregate and per-worker sensors.

## Working in this repository

- Read `README.md` before changing source-specific configuration or sensor behavior.
- Keep Hashvault payout fields separate from XMRig proxy statistics, and preserve dynamic worker sensors when changing coordinator data.
- Before changing CI, check [pschmitt/ci-workflows](https://github.com/pschmitt/ci-workflows) for reusable components and preserve this repository's existing checks.

## Validation

- Run `uvx ruff check .` and `uvx ruff format --check .` for Python changes.
- CI runs Hassfest and the shared Ruff checks; it currently has no test job.
