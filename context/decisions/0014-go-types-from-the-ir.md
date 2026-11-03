# 0014: Go types are emitted from the IR, generated on demand

Status: the publishing part is superseded by [0015](0015-go-and-typescript-are-published.md); the shape of the types stands.

## Context

Decision 0001 left Go for when a consumer existed. The consumers are
CPE simulators and ACS components written in Go, which today keep TR-181
knowledge as string constants. They need typed structs that unmarshal what
an API returns, with the Forum's names and paths at hand.

## Decision

- **A struct per object, a pointer per parameter, a map per table.**
  `*T` makes an absent value `nil` and `omitempty` leaves it out;
  `map[int]*Child` is a table keyed by instance number, which
  `encoding/json` serialises with string keys, the shape a table has in
  JSON. Types follow the base type: `int32`, `uint32`, `int64`, `uint64`,
  `bool`, `float64`, `time.Time`, `string` for text and binary.
- **Two tags per field.** `json` carries the Forum's name, `bbf` the schema
  path, so a Go program can derive the data paths it needs from the struct
  itself without a second table.
- **Enumerations are strings.** A Go enum per enumeration would be
  thousands of constant blocks for little gain; the JSON Schema and the IR
  carry the values for programs that validate.
- **Vendor extras are not kept.** Go has no cheap way to hold unknown
  members beside typed fields; a generated per-struct unmarshaller would
  triple the output. Typed access to a vendor's extensions comes from
  generating the vendor's document, as for Python.
- **The layout is one gofmt leaves alone**: a blank line between fields
  rather than reproducing gofmt's column alignment rules, and the
  typographic quotes gofmt would write in doc comments. The test suite runs
  gofmt, go vet and a JSON round trip over the emitted TR-181 package when
  a Go toolchain is present, and CI installs one.
- **Generated on demand, not published.** Go modules are consumed from a
  repository path, so publishing would mean a repository of generated code
  per release. That is a separate decision for when a consumer asks; until
  then `bbfmodels go` writes the package into the consumer's tree.

## Consequences

- `bbfmodels go` is the command; the Python API is `go_package` and
  `write_go_package`.
- TR-181 USP emits 3.5 MB of Go across 93 files with descriptions.
