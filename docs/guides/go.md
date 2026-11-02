# Go

Every release publishes the Go types of each shipped model to the module
`github.com/ispx-limited/bbfmodels-go`, one package per document, tagged
with the bbfmodels version:

```sh
go get github.com/ispx-limited/bbfmodels-go/tr181usp@latest
```

```go
import "github.com/ispx-limited/bbfmodels-go/tr181usp"

var device tr181usp.Device
json.Unmarshal(body, &device)
*device.WiFi.Radio[1].Channel   // 36
```

The packages are `tr181cwmp`, `tr181usp`, `tr098`, `tr1041`, `tr104cwmp`,
`tr104usp`, `tr135cwmp`, `tr135usp`, `tr140cwmp`, `tr140usp`, `tr196cwmp`,
`tr196usp` and `tr517usp`. For any other document, a vendor's included,
`go` writes the same types into a directory of your own, one file per
top-level subtree:

```sh
bbfmodels go vendor-datamodel.xml --package acmegw -o internal/acmegw
```

```go
// tr181cwmp/wifi.go, generated
// WiFi_Radio is Device.WiFi.Radio.{i}.
type WiFi_Radio struct {
	// readWrite. Enables or disables the interface.
	Enable *bool `json:"Enable,omitempty" bbf:"Device.WiFi.Radio.{i}.Enable"`

	// readWrite. The current radio channel used by the connection.
	Channel *uint32 `json:"Channel,omitempty" bbf:"Device.WiFi.Radio.{i}.Channel"`

	Stats *WiFi_Radio_Stats `json:"Stats,omitempty" bbf:"Device.WiFi.Radio.{i}.Stats."`
}
```

A struct per object, named like the Python class; a pointer field per
parameter, so an absent value is `nil` and `omitempty` leaves it out; a
child object as a pointer; a table as `map[int]*Child` keyed by instance
number, which `encoding/json` writes and reads with string keys, the way a
table serialises. Every field carries the Forum's name in its `json` tag
and its schema path in a `bbf` tag, so a program can walk a struct's tags
to build the paths it asks an ACS for.

| Base type | Go |
| --- | --- |
| `string`, `hexBinary`, `base64` | `*string` |
| `int`, `unsignedInt`, `long`, `unsignedLong` | `*int32`, `*uint32`, `*int64`, `*uint64` |
| `boolean` | `*bool` |
| `dateTime` | `*time.Time` |
| `decimal` | `*float64` |
| any list | `[]T` |

Enumerations are plain strings: a Go program that validates against the
Forum's values reads them from the JSON Schema or the IR. Command inputs
and outputs and event payloads are structs named like the Python classes
(`IP_Diagnostics_TraceRoute_Input`, `Device_Boot_Event`).

The output is laid out so gofmt leaves it unchanged, passes `go vet`, and
a JSON document that a generated Python model dumps unmarshals into it.
Vendor members the model does not define are not kept by the structs;
generate from the vendor's document for typed access, as for Python.

The module repository is written only by the release workflow; issues and
changes go to bbfmodels.
