# Contributing

Bug reports, corrections against the published models and code are welcome.
Vendor extension documents in the TR-106 schema are especially welcome once
the parser lands, because the tool is only as useful as the range of real
device models it can read.

## Building and testing

```sh
scripts/bootstrap.sh   # installs the pinned Python and dependencies with uv
make test
make lint              # format check, lint and type check, what CI runs
```

## Conventions

- Commits and PR titles read `type(area): imperative summary`, for example
  `fix(parser): a list facet with no item type is a list of strings`. CI
  rejects any other title.
- One change per PR. PRs are squash merged, so the title is the commit.
- Generated files are never edited by hand. Change the generator or the
  source document and regenerate; CI fails when committed output is stale.
- Attribute and class names keep the Forum's PascalCase verbatim.
- The tool carries no knowledge of any vendor or product. Vendor behaviour
  comes from a vendor's own data model document, never from code.
