# 0013: JSON Schema and TypeScript are emitted from the IR and published with each release

## Context

Decision 0001 promised outputs beyond Python from the one IR. The first is
JSON Schema, because it is the format other tools already read: API
frameworks, validators, documentation generators and the generators of
typed bindings for several languages. Three questions had to be settled:
what the instance it describes looks like, how strict it is, and where it
lives given that TR-181's schema is three megabytes.

## Decision

- **The instance is a device as nested JSON**, not the flat path and
  value list: an object per data model object, a property per parameter,
  a table as an object keyed by instance number
  (`patternProperties: ^[1-9][0-9]*$`). That is what a generated model
  dumps to and what an API returns, and it gives every object a
  definition under `$defs`, named like the Python class, that other
  outputs can reference.
- **Nothing is required and additional properties are allowed**, as in
  decision 0006.
- **Constraints are emitted by default and dropped by `lenient`.** A
  schema consumer asks for the Forum's ranges, sizes, patterns and
  enumerations; a consumer validating what real devices return wants
  types only. The two are one flag apart, and the enumeration values stay
  available in `x-bbf-enum` in lenient mode.
- **Forum metadata travels in `x-bbf-*` members** where the schema has no
  keyword: path, access, status, version, units, data type, path
  references, table arity and unique keys, mandatory arguments, command
  and event markers.
- **Schemas are release assets, not repository files.** TR-181's schema is
  3.3 MB with descriptions; thirteen of them would double the repository
  on every regeneration. The publish workflow emits them and attaches
  them to the GitHub release, which gives each version a stable URL.
- **TypeScript is emitted from the IR directly**, not from this schema
  through a converter. A converter would turn an enumeration into a
  closed union and lose vendor values, where the IR lets the emitter
  write `"2.4GHz" | "5GHz" | (string & {})` and keep both completion and
  leniency, the same trade the Python models make (decision 0010).

The TypeScript module follows the Python package shape: an interface per
object named like the Python class, `Instances<T>` for a table, a template
literal index signature admitting `X_` vendor members as `unknown` so a
misspelt standard name stays an error, and `Commands` and `Events` maps by
path. Descriptions become doc comments. The declarations are release
assets like the schemas; an npm package is a later decision, taken when
someone needs one.

## Consequences

- `bbfmodels jsonschema` and `bbfmodels typescript` are the commands; the
  Python APIs are `document_schema` and `declarations`.
- The test suite validates a generated model's dump against the schema
  of its document, so the two outputs cannot drift apart silently.
