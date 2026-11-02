# JSON Schema

`jsonschema` writes the JSON Schema (draft 2020-12) of a document's model:
a device as nested JSON, an object per data model object, a property per
parameter, a table as an object keyed by instance number. Every object is a
definition under `$defs`, named like the generated Python class, so a
consumer in any language can reference one object's shape.

```sh
bbfmodels jsonschema tr-181-2-21-0-cwmp-full.xml -o tr181.schema.json --indent 2
bbfmodels jsonschema tr-181-2-21-0-cwmp-full.xml --lenient --no-descriptions -o tr181.lean.json
```

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "urn:bbfmodels:urn:broadband-forum-org:tr-181-2-21-0-cwmp",
  "title": "Device:2.21",
  "$ref": "#/$defs/Device",
  "$defs": {
    "WiFi_Radio": {
      "type": "object",
      "x-bbf-path": "Device.WiFi.Radio.{i}.",
      "x-bbf-table": {"minEntries": 0, "maxEntries": null, "numEntriesParameter": "RadioNumberOfEntries", "uniqueKeys": [["Alias"], ["Name"]]},
      "properties": {
        "Channel": {"type": "integer", "minimum": 1, "maximum": 255, "x-bbf-access": "readWrite", "description": "..."},
        "SupportedFrequencyBands": {"type": "array", "items": {"type": "string", "enum": ["2.4GHz", "5GHz", "6GHz"]}, "x-bbf-list": true},
        "Stats": {"$ref": "#/$defs/WiFi_Radio_Stats"}
      },
      "additionalProperties": true
    }
  }
}
```

Nothing is `required` and additional properties are allowed, as in the
generated models: no device exposes the whole model and vendor parameters
are data. A table is `patternProperties` keyed by `^[1-9][0-9]*$`.

## Types and constraints

| Base type | Schema |
| --- | --- |
| `string` | `string`, with `minLength`, `maxLength`, `pattern` and `enum` from the facets |
| `int`, `unsignedInt`, `long`, `unsignedLong` | `integer` with `minimum` and `maximum` from the ranges, or the type's bounds |
| `boolean` | `boolean` |
| `dateTime` | `string` with `format: date-time` |
| `hexBinary` | `string` matching hex pairs |
| `base64` | `string` with `contentEncoding: base64` |
| `decimal` | `number` |
| any list | `array` of the item schema, with `minItems` and `maxItems` |

The Forum's constraints are emitted because a schema consumer asks for
them. `--lenient` leaves them out and keeps types only, for validating
what real devices return; the enumeration values then travel in
`x-bbf-enum`. A parameter that takes its values from another parameter
has `x-bbf-enumerationRef` instead of `enum` in either mode.

Forum metadata the schema has no keyword for travels in `x-bbf-*`
members: `x-bbf-path`, `x-bbf-access`, `x-bbf-status`, `x-bbf-version`,
`x-bbf-units`, `x-bbf-datatype`, `x-bbf-pathRef`, `x-bbf-table`,
`x-bbf-mandatory` on command arguments.

## Commands and events

In a USP document every command's input and output and every event's
payload is a definition too, named like the Python class
(`IP_Diagnostics_TraceRoute_Output`, `Device_Boot_Event`) and marked with
`x-bbf-command` (`path`, `side`, `async`) or `x-bbf-event`. Objects inside
an output are definitions of their own, referenced as tables.

## Python

```python
from bbfmodels.jsonschema import document_schema
from bbfmodels.parser import parse_file
from bbfmodels.sources import fetch

schema = document_schema(parse_file(fetch("tr-181-2-21-0-cwmp-full.xml")), lenient=True)
```

The output of a generated model validates against the schema of its
document: `Device.from_flat(values).model_dump(mode="json", by_alias=True, exclude_none=True)`.

## Published schemas

Every release attaches the schema of each shipped package to the GitHub
release, with descriptions and with constraints, as
`<package>.schema.json`.
