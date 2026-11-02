# 0010: One generated package per document, lenient on input, strict in `problems`

## Context

Decision 0005 settled on pydantic models built lazily. Generating them
raised questions the decision did not answer: how packages and classes are
named, what a field's type is when the model gives an enumeration or a
range, how values the model does not allow are treated, and how a Forum
parameter can be named like a Python helper.

## Decision

- **One package per published document**, named after it: `tr181_cwmp`,
  `tr181_usp`, `tr098`. The CWMP and USP editions of TR-181 differ in
  commands, events and a few objects, and a user works against one of
  them. The package ships the IR it was generated from as `ir.json.gz`
  and exposes it through `schema()`.
- **A class per object, a module per top-level subtree.** The root object
  is a class named after it (`Device`) in `device.py`; every other object
  is `WiFi_Radio_Stats`, its path with the root dropped, in `wifi.py`.
  Children are emitted before parents, annotations are evaluated eagerly
  rather than as strings, and every helper is imported under a
  leading-underscore alias. Together these make a class body resolve a
  class name before a field of the same name exists in it, and keep a
  parameter named `Param` (TR-181 has one) from shadowing the helper.
  The class's own metadata, its schema path and the package holding its
  IR, lives in dunder attributes (`__bbf_path__`, `__bbf_package__`):
  Forum names never start with an underscore, so nothing can collide with
  them, and pydantic leaves dunder names alone.
- **Types coerce, facets report.** A field's type is the parameter's
  Python type: `int`, `bool`, `datetime`, `bytes`, `Decimal`, `str`, or a
  comma-list of one of them. Ranges, sizes, patterns and enumerations are
  not pydantic constraints, because a real device returns out-of-range
  values and vendor enumeration members and a model that rejects them
  cannot hold what the device said (decision 0006). `problems()` reports
  every facet violation from the shipped IR instead. An enumeration is
  typed `Literal[...] | str`, so an editor completes the Forum's values and
  any other string still validates.
- **Everything optional, tables are `dict[int, Child]`, unknown paths are
  kept** as pydantic extras, nested dicts for unknown objects, and
  `flatten()` writes them back. `flatten()` writes canonical text (`true`,
  not `1`) because the model holds typed values, not wire text; the data
  tree (decision 0009) is the exact round-trip surface.
- **No descriptions in generated code.** They are three megabytes for
  TR-181 and live in the shipped IR, reachable through `schema()`.

## Consequences

- `import bbfmodels.tr181_cwmp` takes about a third of a second and the
  first validation about a fifth; the test suite asserts a ceiling.
- A field whose Forum name collides with a pydantic attribute is emitted
  with a trailing underscore and an alias of the original name, so wire
  conversion is unaffected. None of the shipped documents needs it today.
- Generated code is excluded from the formatter and the linter, and
  type-checked like the rest of the package.
