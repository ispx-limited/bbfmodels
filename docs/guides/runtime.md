# Schema, tree and codec

The runtime works from the IR with no generated code: load the documents a
device is described by, resolve paths, hold the device's values, convert
them, validate them.

## Schema

A `Schema` indexes one or more documents by schema path, the path with
`{i}` where the specification has it. A service model such as TR-104
mounts under the root's `Services.` object, which is where it sits on a
real device.

```python
from bbfmodels.parser import parse_file
from bbfmodels.schema import Schema
from bbfmodels.sources import fetch

schema = Schema.from_documents(
    parse_file(fetch("tr-181-2-21-0-cwmp-full.xml")),
    parse_file(fetch("tr-104-2-0-2-cwmp-full.xml")),
)
schema.object("Device.WiFi.Radio.{i}.").num_entries_parameter   # 'RadioNumberOfEntries'
schema.parameter("Device.WiFi.Radio.{i}.Channel").access          # <Access.READ_WRITE: 'readWrite'>
[o.name for o in schema.children("Device.WiFi.")][:3]             # ['MultiAP', 'DataElements', 'Templates'], document order
"Device.Services.VoiceService.{i}.Capabilities." in schema.objects   # True
```

`resolve` takes a data path, with instance numbers, and returns the object,
the parameter and the instance numbers. A table addressed without an
instance resolves to the table itself; a parameter directly under a table
does not resolve, because parameters belong to instances.

```python
r = schema.resolve("Device.WiFi.Radio.2.Channel")
r.object.path, r.parameter.name, r.instances   # 'Device.WiFi.Radio.{i}.', 'Channel', (2,)
r.schema_path                                  # 'Device.WiFi.Radio.{i}.Channel'
Schema.data_path("Device.WiFi.SSID.{i}.SSID", 1)   # 'Device.WiFi.SSID.1.SSID'
schema.resolve("Device.WiFi.Radio.2.X_ACME_Power")   # raises UnknownPath
```

A vendor's document is added like any other, and its `X_` paths then
resolve.

## Tree

A `Tree` holds the flat path and value pairs a device returns, arranged as
objects, tables and instances. It stores the wire text exactly as received,
decodes through the schema when a value is read, and writes the stored text
back out, so a tree flattens to exactly what built it. Paths the schema does
not define are kept where they belong.

```python
from bbfmodels.tree import Tree

tree = Tree.from_flat(schema, {
    "Device.WiFi.Radio.1.Enable": "1",
    "Device.WiFi.Radio.1.Channel": "36",
    "Device.WiFi.Radio.1.SupportedFrequencyBands": "2.4GHz,5GHz",
    "Device.WiFi.Radio.1.X_ACME_TxPower": "high",
})
radio = tree["Device"]["WiFi"]["Radio"][1]
radio.value("Enable"), radio.value("Channel")   # True, 36
radio.value("SupportedFrequencyBands")           # ['2.4GHz', '5GHz']
radio.text("Enable")                             # '1', exactly as received
radio.unknown_parameters                         # ['X_ACME_TxPower']
tree.set("Device.WiFi.Radio.1.Channel", 999)
tree.problems()        # [('Device.WiFi.Radio.1.Channel', '999 is outside the allowed ranges')]
tree.flatten()         # the same keys, in the same order, with the one changed value
```

`set` encodes a Python value for the parameter's syntax; `set_text` stores
text as is. Neither validates: `problems` reports every facet violation in
the tree, because a device's out-of-range value is something to hold and
report, not to refuse.

## Codec

The codec is the rule for writing each TR-106 base type as text. `decode`
and `encode` convert one parameter's value; `problems` checks text against
a syntax.

| Base type | Python | Wire text |
| --- | --- | --- |
| `string` | `str` | as is |
| `int`, `unsignedInt`, `long`, `unsignedLong` | `int` | decimal |
| `boolean` | `bool` | `true` or `false` on the way out; `1`, `0`, `true`, `false` accepted |
| `dateTime` | `datetime` with a time zone | ISO 8601, `Z` for UTC; `0001-01-01T00:00:00Z` is the Unknown Time |
| `hexBinary` | `bytes` | upper-case hex |
| `base64` | `bytes` | base64 |
| `decimal` | `Decimal` | decimal |
| any list | `list[...]` | comma-separated items |

```python
from bbfmodels import codec

syntax = schema.parameter("Device.WiFi.Radio.{i}.SupportedFrequencyBands").syntax
codec.decode(syntax, "2.4GHz, 5GHz")      # ['2.4GHz', '5GHz']
codec.encode(syntax, ["5GHz"])             # '5GHz'
codec.problems(schema.parameter("Device.WiFi.Radio.{i}.Channel").syntax, "999")
# ['999 is outside the allowed ranges']
```

`problems` checks the base type's bounds, ranges with their step, sizes,
enumerations (unless the parameter takes its values from another parameter
through an enumeration reference), patterns, and list bounds.
