# bbfmodels

Typed models and schema tooling for Broadband Forum data models (TR-181,
TR-098, TR-104 and the rest), generated from the XML the Forum publishes.

The Forum defines what a broadband gateway exposes to its management system
as XML in the TR-106 schema: thousands of objects and parameters, their types,
ranges, enumerations, writability and multi-instance tables. Everyone who
builds against those models, an ACS, a USP controller, a device simulator, an
integration script, re-derives the same facts from the same XML and hand-types
the same parameter paths as strings. bbfmodels does it once:

- A parser that reads the published XML into a normalised intermediate
  representation, published as JSON with its own schema.
- A Python runtime that works from that representation: resolve a path,
  validate a value against the model's constraints, convert between the flat
  path and value lists that CWMP and USP carry on the wire and a typed tree.
- Generated typed bindings: pydantic models for Python first, JSON Schema and
  TypeScript from the same representation, Go when there is a consumer.

Names stay as the Forum wrote them. `Device.WiFi.SSID.{i}.SSID` is a table of
`SSID` entries indexed by instance number, and the attribute is `SSID`, not
`ssid`.

## Status

Pre-release. The parser and the intermediate representation are in place:
`bbfmodels fetch` downloads the Forum's published documents and
`bbfmodels ir` turns one into JSON. The runtime comes next, then generated
Python models. Until the first release there is no package on PyPI.

The design decisions behind the code are in `context/decisions/`, indexed in
`context/README.md`. Read them before changing the parser or the IR.

## Development

Prerequisites: git and [uv](https://docs.astral.sh/uv/). The pinned Python is
installed by uv.

```sh
scripts/bootstrap.sh
make test
make lint
```

`make help` lists the rest. Documentation is built from `docs/` with
`make docs` and published at https://docs.bbfmodels.ispx.co/.

## Licence

Apache-2.0, copyright ISPX LIMITED. The Broadband Forum publishes its data
models under the BSD 3-clause licence; output derived from them carries the
Forum's notice.
