# 0001: One parser, one intermediate representation, several emitters

## Context

The Forum publishes its data models as XML in the TR-106 schema. The goal
is typed bindings in more than one language, plus a runtime that can work
with a model without generated code. Each of those consumers needs the same
facts: objects and their arity, parameters and their types, facets,
writability, status, references, commands and events. Parsing the XML in
each consumer would mean several parsers that disagree about the corner
cases of the same documents.

## Decision

The XML is parsed once into an intermediate representation (IR), defined in
`src/bbfmodels/ir.py`. Every consumer, the runtime and every code
generator, reads the IR and never the XML. A new target language is an
emitter over the IR, not a second parser.

The IR is fully resolved: a parameter's syntax carries its effective base
type and facets with named data types already applied through their
inheritance chain, so no consumer needs a second lookup. The name of the
data type is kept too, for emitters that generate one named type and refer
to it. The IR serialises to JSON and publishes its own JSON Schema, so a
consumer in another language can read it without this package.

## Consequences

- A parsing fix lands once and every output picks it up on regeneration.
- The IR is the contract. Changing it is a change to every emitter and is
  treated as a breaking change once the package is past 1.0.
- The IR is lossless where it matters for generation and validation, and
  deliberately not a mirror of the XML: templates, bibliography and the
  `dmr:` report attributes are not carried.
