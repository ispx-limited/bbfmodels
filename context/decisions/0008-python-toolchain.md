# 0008: Python toolchain: uv, ruff, mypy, pytest, standard library XML

## Context

The tool needs one environment manager, one formatter and linter, one type
checker and one test runner, chosen once so contributors do not debate
them.

## Decision

- Python 3.11 or later, so `StrEnum` and modern typing are available
  without compatibility shims.
- uv manages the environment and the lockfile; `uv.lock` is committed.
- ruff formats and lints; its output is the standard and is not argued with.
- mypy runs in strict mode over the package.
- pytest runs the tests.
- The XML is read with the standard library's `xml.etree` after the repair
  pass described in [0003](0003-parse-the-flattened-full-documents.md).
  lxml would tolerate more but adds a compiled dependency for a problem
  the repair pass already solves.

## Consequences

- `scripts/bootstrap.sh` is `uv sync` plus the checks, and a fresh clone is
  working in one command.
- CI runs the same four commands as `make lint` and `make test`, on every
  supported Python.
