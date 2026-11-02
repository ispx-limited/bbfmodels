# Quickstart

bbfmodels is pre-release and not yet on PyPI, so it runs from a clone.
Prerequisites: git and [uv](https://docs.astral.sh/uv/).

```sh
git clone https://github.com/ispx-limited/bbfmodels.git
cd bbfmodels
scripts/bootstrap.sh
```

## Fetch the published documents

The Forum publishes every data model as a flattened `-full.xml` document.
`fetch` downloads into a local cache (`~/.cache/bbfmodels`, or
`$BBFMODELS_CACHE`) and reuses what is already there.

```sh
uv run bbfmodels fetch                           # the core set: TR-098, TR-104, TR-135, TR-140, TR-157, TR-181
uv run bbfmodels fetch tr-181-2-21-0-usp-full.xml
uv run bbfmodels fetch --list usp                # everything the Forum publishes for USP
```

## Turn a document into its IR

`ir` parses a document and writes the intermediate representation as JSON.
Everything else in bbfmodels reads this representation, never the XML.

```sh
uv run bbfmodels ir ~/.cache/bbfmodels/tr-181-2-21-0-cwmp-full.xml -o tr-181.json --indent 2
```

The output has the document's data types and models, each model's objects
keyed by path, and each object's parameters, commands and events:

```json
{
  "spec": "urn:broadband-forum-org:tr-181-2-21-0-cwmp",
  "protocol": "cwmp",
  "models": [
    {
      "name": "Device:2.21",
      "objects": {
        "Device.WiFi.Radio.{i}.": {
          "path": "Device.WiFi.Radio.{i}.",
          "access": "readOnly",
          "min_entries": 0,
          "max_entries": null,
          "num_entries_parameter": "RadioNumberOfEntries",
          "parameters": {
            "Channel": {
              "name": "Channel",
              "access": "readWrite",
              "syntax": {
                "base_type": "unsignedInt",
                "facets": { "ranges": [{ "min_inclusive": 1, "max_inclusive": 255 }] }
              }
            }
          }
        }
      }
    }
  ]
}
```

Fields at their default are left out: an object without `status` is
current, a parameter without `list` is a single value. The JSON Schema of
the representation is `uv run bbfmodels ir-schema`.

## Use it from Python

```python
from bbfmodels.parser import parse_file

doc = parse_file("tr-181-2-21-0-cwmp-full.xml")
radio = doc.models[0].objects["Device.WiFi.Radio.{i}."]
print(radio.multi_instance, radio.num_entries_parameter)
channel = radio.parameters["Channel"].syntax
print(channel.base_type, channel.facets.ranges[0].max_inclusive)
```
