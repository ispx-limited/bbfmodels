# 0005: Generated Python models are pydantic, built lazily per subtree

## Context

The Python bindings could be plain classes, dataclasses or pydantic models.
TR-181 alone has more than twelve thousand parameters in some fifteen
hundred objects. A single eagerly built module of that size takes seconds
to import, which rules out the obvious implementation of any of the three.

## Decision

Generated Python models are pydantic v2 models. Validation against the
model's facets (ranges, sizes, enumerations, patterns, list bounds) is half
of what the bindings are for, and pydantic is what integrators already use
with their web frameworks and clients, so the generated models drop in
unchanged.

Models build lazily and are split into one module per top-level subtree
(`Device.WiFi`, `Device.IP`, and so on), so importing one subtree pays for
that subtree only.

## Consequences

- pydantic is the package's one runtime dependency.
- Import time is measured in the test suite and a regression fails it.
- Dataclasses would have saved the dependency and lost validation; that
  trade was considered and rejected.
