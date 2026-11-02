# Quickstart

```sh
pip install bbfmodels
```

Python 3.11 or later. To work on bbfmodels itself, clone the repository and
run `scripts/bootstrap.sh`; it needs git and [uv](https://docs.astral.sh/uv/).

## Fetch the published documents

The Forum publishes every data model as a flattened `-full.xml` document.
`fetch` downloads into a local cache (`~/.cache/bbfmodels`, or
`$BBFMODELS_CACHE`) and reuses what is already there.

```sh
bbfmodels fetch                                  # the core set: TR-098, TR-104, TR-135, TR-140, TR-157, TR-181
bbfmodels fetch tr-181-2-21-0-usp-full.xml
bbfmodels fetch --list usp                       # everything the Forum publishes for USP
```

## Turn a document into its IR

`ir` parses a document and writes the intermediate representation as JSON.
Everything else in bbfmodels reads this representation, never the XML.

```sh
bbfmodels ir ~/.cache/bbfmodels/tr-181-2-21-0-cwmp-full.xml -o tr-181.json --indent 2
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
the representation is `bbfmodels ir-schema`.

## Use it from Python

```python
from bbfmodels.parser import parse_file

doc = parse_file("tr-181-2-21-0-cwmp-full.xml")
radio = doc.models[0].objects["Device.WiFi.Radio.{i}."]
print(radio.multi_instance, radio.num_entries_parameter)
channel = radio.parameters["Channel"].syntax
print(channel.base_type, channel.facets.ranges[0].max_inclusive)
```

## Work with a device's values

A `Schema` indexes one or more documents by path. A service model such as
TR-104 mounts under the root's `Services.` object, where it sits on a real
device.

```python
from bbfmodels.parser import parse_file
from bbfmodels.schema import Schema

schema = Schema.from_documents(
    parse_file("tr-181-2-21-0-cwmp-full.xml"),
    parse_file("tr-104-2-0-2-cwmp-full.xml"),
)
r = schema.resolve("Device.WiFi.Radio.2.Channel")
print(r.schema_path, r.instances)  # Device.WiFi.Radio.{i}.Channel (2,)
print(Schema.data_path("Device.WiFi.SSID.{i}.SSID", 1))  # Device.WiFi.SSID.1.SSID
print("Device.Services.VoiceService.{i}." in schema.objects)  # True
```

A `Tree` holds the flat path and value pairs a device returns, arranged as
objects, tables and instances. Values decode through the schema when read
and the text comes back out exactly as it went in, vendor parameters
included.

```python
from bbfmodels.tree import Tree

tree = Tree.from_flat(
    schema,
    {
        "Device.WiFi.Radio.1.Enable": "1",
        "Device.WiFi.Radio.1.Channel": "36",
        "Device.WiFi.Radio.1.SupportedFrequencyBands": "2.4GHz,5GHz",
        "Device.WiFi.Radio.1.X_EXAMPLE_TxPower": "high",
    },
)
radio = tree["Device"]["WiFi"]["Radio"][1]
print(radio.value("Enable"), radio.value("Channel"))  # True 36
print(radio.value("SupportedFrequencyBands"))  # ['2.4GHz', '5GHz']
print(radio.unknown_parameters)  # ['X_EXAMPLE_TxPower']
tree.set("Device.WiFi.Radio.1.Channel", 999)
print(tree.problems())  # [('Device.WiFi.Radio.1.Channel', '999 is outside the allowed ranges')]
print(tree.flatten()["Device.WiFi.Radio.1.Enable"])  # 1
```

## Use the generated models

Three packages ship with typed models: `bbfmodels.tr181_cwmp`,
`bbfmodels.tr181_usp` and `bbfmodels.tr098`. Every object is a class, every
parameter a typed optional field, every table a `dict[int, Child]`. Names
are the Forum's names.

```python
from bbfmodels.tr181_cwmp import Device

device = Device.from_flat(
    {
        "Device.DeviceInfo.UpTime": "1234",
        "Device.WiFi.Radio.1.Enable": "1",
        "Device.WiFi.Radio.1.Channel": "36",
        "Device.WiFi.Radio.1.SupportedFrequencyBands": "2.4GHz,5GHz",
        "Device.WiFi.Radio.1.X_EXAMPLE_TxPower": "high",
    }
)
radio = device.WiFi.Radio[1]
print(device.DeviceInfo.UpTime, radio.Enable, radio.Channel)  # 1234 True 36
print(radio.SupportedFrequencyBands)  # ['2.4GHz', '5GHz']
print(radio.X_EXAMPLE_TxPower)  # high, kept as text
radio.Channel = 999
print(device.problems())  # [('Device.WiFi.Radio.1.Channel', '999 is outside the allowed ranges')]
print(device.flatten()["Device.WiFi.Radio.1.Enable"])  # true
```

Values coerce to their Python type on the way in. The model's ranges,
sizes, patterns and enumerations are not enforced at that point, because a
real device returns values outside them; `problems()` reports every
violation against the shipped schema instead.

Classes construct directly, and `flatten` takes the data path to write
under:

```python
from bbfmodels.tr181_cwmp.wifi import WiFi_Radio

WiFi_Radio(Enable=True, Channel=36).flatten("Device.WiFi.Radio.1.")
# {'Device.WiFi.Radio.1.Enable': 'true', 'Device.WiFi.Radio.1.Channel': '36'}
```

Any document in the TR-106 schema generates the same way, a vendor's
extensions included:

```sh
bbfmodels generate vendor-model-full.xml --package acme.models --root src
```
