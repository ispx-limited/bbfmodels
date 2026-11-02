# Go

`go` writes the Go types of a document's model into a directory, one file
per top-level subtree, ready to import as a package:

```sh
bbfmodels go tr-181-2-21-0-cwmp-full.xml --package tr181cwmp -o internal/tr181cwmp
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

```go
var device tr181cwmp.Device
json.Unmarshal(body, &device)
*device.WiFi.Radio[1].Channel   // 36
```

The Go types are generated on demand with the command above. A published
Go module is a later step, taken when someone needs one.
