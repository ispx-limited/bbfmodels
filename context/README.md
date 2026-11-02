# Design memory

This directory is the project's design memory: the decisions that shape
the code and the reasons behind them, so a contributor, or a coding agent
working with one, can change the code without undoing a decision by
accident. Read it before touching the parser, the IR or a generator.

`decisions/` holds one record per significant decision: context, decision,
consequences, in a page or less. Records are append-only. When a decision
changes, a new record is written and the old one is marked superseded.

| Number | Title | Status |
| --- | --- | --- |
| [0001](decisions/0001-one-parser-one-ir-several-emitters.md) | One parser, one intermediate representation, several emitters | Accepted |
| [0002](decisions/0002-names-stay-as-the-forum-wrote-them.md) | Names stay as the Forum wrote them | Accepted |
| [0003](decisions/0003-parse-the-flattened-full-documents.md) | Parse the Forum's flattened full documents | Accepted |
| [0004](decisions/0004-generated-output-is-committed.md) | Generated output is committed and checked for drift | Accepted |
| [0005](decisions/0005-python-models-are-pydantic.md) | Generated Python models are pydantic, built lazily per subtree | Accepted |
| [0006](decisions/0006-everything-optional-unknown-paths-kept.md) | Everything is optional and unknown paths round-trip | Accepted |
| [0007](decisions/0007-vendor-extensions-are-overlays.md) | Vendor extensions are overlays in the same schema | Accepted |
| [0008](decisions/0008-python-toolchain.md) | Python toolchain: uv, ruff, mypy, pytest, standard library XML | Accepted |
| [0009](decisions/0009-the-tree-keeps-wire-text.md) | The data tree keeps wire text and decodes on demand | Accepted |
| [0010](decisions/0010-generated-python-packages.md) | One generated package per document, lenient on input, strict in `problems` | Accepted |
| [0011](decisions/0011-typed-paths-are-a-stub-over-the-schema.md) | Typed paths are a generic runtime plus a stub, not generated classes | Accepted |
| [0012](decisions/0012-commands-and-events-have-argument-paths.md) | Commands and events get argument paths, and classes named by owner | Accepted |
| [0013](decisions/0013-json-schema-from-the-ir.md) | JSON Schema and TypeScript are emitted from the IR and published with each release | Accepted |
