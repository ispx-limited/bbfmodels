# Quickstart

```sh
pip install bbfmodels
```

Python 3.11 or later; the one runtime dependency is pydantic.

## Typed models of a device

The packages `bbfmodels.tr181_cwmp`, `bbfmodels.tr181_usp`, `bbfmodels.tr098`
and the service models ship with the package. Build a model from the path
and value pairs an ACS returns and read typed values:

```python
from bbfmodels.tr181_cwmp import Device

device = Device.from_flat({
    "Device.DeviceInfo.UpTime": "1234",
    "Device.WiFi.Radio.1.Enable": "1",
    "Device.WiFi.Radio.1.Channel": "36",
    "Device.WiFi.Radio.1.SupportedFrequencyBands": "2.4GHz,5GHz",
})
radio = device.WiFi.Radio[1]
radio.Channel                     # 36
radio.SupportedFrequencyBands     # ['2.4GHz', '5GHz']
device.problems()                 # [] : every value is within the model's constraints
device.flatten()                  # back to path and text pairs
```

The [models guide](models.md) covers construction, validation, tables,
vendor parameters and the service models.

## Resolve and validate paths without generated code

```python
from bbfmodels.parser import parse_file
from bbfmodels.schema import Schema
from bbfmodels.sources import fetch

schema = Schema.from_documents(parse_file(fetch("tr-181-2-21-0-cwmp-full.xml")))
r = schema.resolve("Device.WiFi.Radio.2.Channel")
r.schema_path                     # 'Device.WiFi.Radio.{i}.Channel'
r.parameter.syntax.facets.ranges  # (Range(min_inclusive=1, max_inclusive=255, step=None),)
```

The [runtime guide](runtime.md) covers the schema, the data tree and the
codec.

## Generate models for a vendor's document

```sh
bbfmodels generate vendor-datamodel.xml --package acme.gateway --root src
```

The [vendor models guide](vendor-models.md) walks through a real vendor
document from the Forum's XML to typed access to its `X_` extensions.
