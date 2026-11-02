# Documents and the IR

The Broadband Forum publishes each data model as XML in the TR-106 schema,
in two forms. The modular files assemble objects from imports and reusable
components; the flattened `-full.xml` files have all of that resolved.
bbfmodels reads the flattened form only.

## Fetching

`fetch` downloads a document into a local cache, `~/.cache/bbfmodels` or
`$BBFMODELS_CACHE`, and reuses what is there. Published files never change.

```sh
bbfmodels fetch                                  # the core set
bbfmodels fetch tr-181-2-21-0-usp-full.xml       # one document
bbfmodels fetch --list cwmp                      # everything published for CWMP
bbfmodels fetch --list usp
```

The core set is TR-098, TR-104 (both issues), TR-135, TR-140, TR-157,
TR-181 (CWMP and USP), TR-196 and TR-517. The same call exists in Python:

```python
from bbfmodels.sources import fetch, available, CORE

path = fetch("tr-181-2-21-0-cwmp-full.xml")
```

## The intermediate representation

`ir` parses a document into the intermediate representation (IR), the one
structure everything else in bbfmodels reads:

```sh
bbfmodels ir tr-181-2-21-0-cwmp-full.xml -o tr-181.json --indent 2
bbfmodels ir-schema > ir-schema.json             # the IR's JSON Schema
```

A document has named data types and models. A model has objects keyed by
path, with `{i}` marking a table exactly as the specification writes it.
An object has parameters, and in USP documents commands and events; a
parameter has a syntax with its base type, the name of its data type if it
used one, and its facets.

```json
{
  "spec": "urn:broadband-forum-org:tr-181-2-21-0-cwmp",
  "protocol": "cwmp",
  "models": [{
    "name": "Device:2.21",
    "objects": {
      "Device.WiFi.Radio.{i}.": {
        "path": "Device.WiFi.Radio.{i}.",
        "access": "readOnly",
        "min_entries": 0,
        "max_entries": null,
        "num_entries_parameter": "RadioNumberOfEntries",
        "unique_keys": [{"functional": false, "parameters": ["Alias"]}, {"functional": false, "parameters": ["Name"]}],
        "parameters": {
          "Channel": {
            "name": "Channel",
            "access": "readWrite",
            "syntax": {
              "base_type": "unsignedInt",
              "facets": {"ranges": [{"min_inclusive": 1, "max_inclusive": 255}]}
            }
          }
        }
      }
    }
  }]
}
```

Fields at their default are left out: an object without `status` is
current, a parameter without `list` is a single value, `max_entries` of
`null` is unbounded.

Named data types are resolved. A parameter declared as `IPv4Address` has
`"data_type": "IPv4Address"` and a syntax whose base type and facets are
the fully inherited ones, so no consumer needs a second lookup. The
document's `data_types` table is there for emitters that want to generate
a named type.

In Python:

```python
from bbfmodels.parser import parse_file

doc = parse_file("tr-181-2-21-0-cwmp-full.xml")
model = doc.models[0]
radio = model.objects["Device.WiFi.Radio.{i}."]
radio.multi_instance              # True
radio.name, radio.parent_path     # 'Radio', 'Device.WiFi.'
channel = radio.parameters["Channel"].syntax
channel.base_type                 # <BaseType.UNSIGNED_INT: 'unsignedInt'>
channel.facets.ranges[0].max_inclusive   # 255
reboot = parse_file("tr-181-2-21-0-usp-full.xml").models[0].objects["Device."].commands["Reboot()"]
reboot.input.parameters["Cause"].mandatory   # False
```

## What the parser tolerates

The published documents are not always well-formed XML, and vendor
documents captured from devices depart from the schema in small ways. The
parser repairs what it has seen and warns where it had to decide:

| In the document | What happens |
| --- | --- |
| Bare `&` or literal `<OUI>` markup in prose | Escaped before parsing |
| An attribute published as `value="""` | Read as a quote |
| Whitespace around a name (`name="Queueing "`) | Dropped |
| An empty `<syntax/>` | Read as a string, with a `ParseWarning` |
| An unknown `status`, `access` or `activeNotify` value | The conservative default (`current`, `readOnly`, `normal`), with a `ParseWarning` |
| `<import>` or `<component>` elements | Rejected: use the flattened `-full.xml` edition |

Anything else the schema does not allow is a `ParseError` naming the place.
