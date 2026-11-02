# bbfmodels

Typed models and schema tooling for Broadband Forum data models, generated
from the XML the Forum publishes. The README says what it is for; this file
is for anyone, person or coding agent, working in the repository.

## Layout

- `src/bbfmodels/` is the package. `cli.py` is the command line entry point.
- `tests/` holds the pytest suite.
- `docs/` is the documentation site (mkdocs), built strictly in CI. A page
  exists when it has content; nothing is scaffolded empty.
- `hooks/changelog.py` renders `CHANGELOG.md` and `release-notes/` as the
  docs site's Changelog page. `CHANGELOG.md` is written by the release
  automation and never edited by hand on `main`.

## Commands

- Set up: `scripts/bootstrap.sh`
- Tests: `make test`
- Format, lint, types: `make lint`
- Docs: `make docs`

## Rules

- **The intermediate representation is the contract.** Everything downstream
  of the parser reads the IR, never the XML. A new output language is an
  emitter over the IR, not a second parser.
- **Generated output is committed and never hand-edited.** Change the
  generator or the source document, regenerate, and commit the result. CI
  fails when committed output is stale.
- **Names are the Forum's names.** Objects, parameters, commands and events
  keep their PascalCase spelling verbatim. `{i}` stays in schema paths; data
  paths carry instance numbers.
- **No vendor or product knowledge in code.** Vendor extensions come from
  the vendor's own TR-106 document and generate overlays. No lookup tables
  of OUIs, model names or firmware versions.
- **Everything optional, unknown paths kept.** A real device exposes a
  subset of the model plus parameters the model does not know. A tree
  built from device values keeps what it did not recognise and writes it
  back unchanged.
- **Python is written for Python.** ruff formats and lints, mypy runs
  strict, pytest tests behaviour rather than implementation. New logic
  ships with tests in the same change.
- **Writing style**, in code comments, docs and commit messages: plain
  words, short sentences, no em dashes, no emoji. Comments state what the
  code cannot: a constraint, a reason, a reference to the specification.
- Commits and PR titles read `type(area): imperative summary`. One change
  per PR, squash merged.
