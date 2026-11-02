# Generated models

A generated package has a pydantic class per object, a typed optional
field per parameter and a `dict[int, Child]` per table. Names are the
Forum's names, PascalCase and all. These packages ship with bbfmodels:

| Package | Document | Root class |
| --- | --- | --- |
| `bbfmodels.tr181_cwmp` | TR-181 issue 2, CWMP edition | `Device` |
| `bbfmodels.tr181_usp` | TR-181 issue 2, USP edition | `Device` |
| `bbfmodels.tr098` | TR-098 | `InternetGatewayDevice` |
| `bbfmodels.tr104_1` | TR-104 issue 1, voice on TR-098 gateways | `VoiceService` |
| `bbfmodels.tr104_cwmp`, `bbfmodels.tr104_usp` | TR-104 issue 2, voice | `VoiceService` |
| `bbfmodels.tr135_cwmp`, `bbfmodels.tr135_usp` | TR-135, set-top box | `STBService` |
| `bbfmodels.tr140_cwmp`, `bbfmodels.tr140_usp` | TR-140, storage | `StorageService` |
| `bbfmodels.tr196_cwmp`, `bbfmodels.tr196_usp` | TR-196, femtocell | `FAPService` |
| `bbfmodels.tr517_usp` | TR-517, Matter | `MatterService` |

Each package records `SOURCE`, `SPEC` and `MODEL`, and `schema()` returns
the `Schema` of the IR it was generated from.

## From device values and back

`from_flat` takes the path and value pairs an ACS or USP controller
returns. Values coerce to their Python type: integers, booleans (`1` and
`true` alike), dates, binary, decimals, and comma-separated lists.

```python
from bbfmodels.tr181_cwmp import Device

device = Device.from_flat({
    "Device.DeviceInfo.UpTime": "1234",
    "Device.DeviceInfo.FirstUseDate": "2026-01-02T03:04:05Z",
    "Device.WiFi.Radio.1.Enable": "1",
    "Device.WiFi.Radio.1.Channel": "36",
    "Device.WiFi.SSID.1.LowerLayers": "Device.WiFi.Radio.1",
})
device.DeviceInfo.UpTime           # 1234
device.DeviceInfo.FirstUseDate     # datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)
device.WiFi.Radio[1].Enable        # True
device.WiFi.SSID[1].LowerLayers    # ['Device.WiFi.Radio.1']
device.WiFi.Radio[2]               # KeyError: only instance 1 was given
```

Every field is optional, because no device exposes the whole model, and a
child object that was not given is `None`. Paths may also be relative to
the object: `Device.from_flat({"WiFi.Radio.1.Channel": "36"})`.

`flatten` writes the model back as path and text pairs in canonical form:
`true` for a boolean, `a,b` for a list, upper-case hex for binary.

```python
device.flatten()
# {'Device.DeviceInfo.UpTime': '1234', ..., 'Device.WiFi.Radio.1.Enable': 'true', ...}
```

## Validation

Parsing is lenient on purpose. Ranges, sizes, patterns and enumerations are
not enforced when a model is built, because a real device returns values
outside them and a model that refused them could not hold what the device
said. `problems()` reports every violation against the shipped schema:

```python
device.WiFi.Radio[1].Channel = 999
device.WiFi.Radio[1].Status = "zz"
device.problems()
# [('Device.WiFi.Radio.1.Status', "'zz' is not one of the enumerated values"),
#  ('Device.WiFi.Radio.1.Channel', '999 is outside the allowed ranges')]
```

An enumeration is typed `Literal[...] | str`: an editor completes the
Forum's values, and a vendor's extra value still validates. A parameter
that takes its allowed values from another parameter, as
`OperatingChannelBandwidth` does from `SupportedOperatingChannelBandwidths`,
is not checked against a fixed list, because the list is the device's.

## Tables and construction

A table is a plain `dict[int, Child]`. Classes construct directly, and
`flatten` takes the data path to write under:

```python
from bbfmodels.tr181_cwmp.wifi import WiFi_Radio

radio = WiFi_Radio(Enable=True, Channel=36, OperatingFrequencyBand="5GHz")
radio.flatten("Device.WiFi.Radio.1.")
# {'Device.WiFi.Radio.1.Enable': 'true', 'Device.WiFi.Radio.1.OperatingFrequencyBand': '5GHz', 'Device.WiFi.Radio.1.Channel': '36'}
```

Class names are the object's path with the root dropped and dots replaced:
`WiFi_Radio`, `WiFi_Radio_Stats`, `IP_Interface_IPv4Address`. They live in
the module of their top-level subtree: `bbfmodels.tr181_cwmp.wifi`,
`bbfmodels.tr181_cwmp.ip`.

## Vendor parameters

Parameters and objects the model does not define are kept as pydantic
extras and written back by `flatten`. An unknown parameter is text; an
unknown object is a nested dict with instance numbers as string keys.

```python
device = Device.from_flat({
    "Device.WiFi.Radio.1.X_ACME_TxPower": "high",
    "Device.X_ACME_Mesh.1.Role": "controller",
})
device.WiFi.Radio[1].X_ACME_TxPower   # 'high'
device.X_ACME_Mesh                    # {'1': {'Role': 'controller'}}
device.flatten()                      # both paths come back
```

For typed access to a vendor's extensions, generate a package from the
vendor's document: see [vendor models](vendor-models.md).

## Service models

A service model's root is a table, `VoiceService.{i}.`, that a device
mounts under its `Services.` object. The generated classes carry the
document's paths and the mount is given when converting:

```python
from bbfmodels.tr104_cwmp import VoiceService

voice = VoiceService.from_flat(values, "Device.Services.VoiceService.1.")
voice.Capabilities.MaxLineCount
voice.flatten("Device.Services.VoiceService.1.")
voice.problems("Device.Services.VoiceService.1.")
```

Without a prefix, `from_flat` takes paths relative to the instance
(`Capabilities.MaxLineCount`) and `problems` reports against instance 1.

## Commands and events

The USP packages carry a class for every command's input and output and
every event's payload. `COMMANDS` maps a command path to its two classes
and `EVENTS` an event path to its class, which is how a controller picks
the class for the response to the Operate it sent:

```python
from bbfmodels.tr181_usp import COMMANDS, EVENTS

request_cls, response_cls = COMMANDS["Device.IP.Diagnostics.TraceRoute()"]
request = request_cls(Host="example.net", NumberOfTries=3)
request.flatten("")           # {'Host': 'example.net', 'NumberOfTries': '3'}, the input_args of an Operate

response = response_cls.from_flat({
    "Status": "Complete",
    "ResponseTime": "12",
    "RouteHops.1.Host": "gw",
    "RouteHops.1.RTTimes": "1,2,3",
})
response.RouteHops[1].RTTimes   # [1, 2, 3]
response.problems()             # checked like any parameter

boot = EVENTS["Device.Boot!"].from_flat({"Cause": "LocalReboot"})
```

The classes are importable by name too, `IP_Diagnostics_TraceRoute_Input`
from `bbfmodels.tr181_usp.ip`, named by the owning object, the command
and the side. In the schema the arguments live under
`Device.IP.Diagnostics.TraceRoute().Input.` and `.Output.`, and an event's
under `Device.Boot!.`, which is where `problems()` reports them.

## Names that had to change

Three kinds of Forum name cannot be a Python field as written. The field
gets a safe name and the Forum's name as its alias, so `from_flat` and
`flatten` are unaffected:

| Forum name | Field | Why |
| --- | --- | --- |
| `Config` | `Config_` | pydantic reads `Config` from a class body as its legacy configuration |
| `11kRSSIHighThresholdOffset` | `N11kRSSIHighThresholdOffset` | an identifier cannot start with a digit |
| a name with a hyphen or other symbol | the symbol becomes `_` | not an identifier |

None of the Forum's own documents needs the second or third; vendor
documents do.
