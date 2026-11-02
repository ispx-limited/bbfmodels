# TypeScript

`typescript` writes the TypeScript declarations of a document's model, one
`.d.ts` module per document:

```sh
bbfmodels typescript tr-181-2-21-0-cwmp-full.xml -o tr181_cwmp.d.ts
```

```ts
import type { Root, WiFi_Radio, Commands } from "./tr181_usp";

const radio: WiFi_Radio = {
  Enable: true,
  Channel: 36,
  OperatingChannelBandwidth: "80MHz",   // completes; any other string also type checks
  X_ACME_TxPower: "high",               // vendor members are admitted as unknown
};
const device: Root = { WiFi: { Radio: { 1: radio } } };
type TraceRoute = Commands["Device.IP.Diagnostics.TraceRoute()"]["output"];
```

An interface per object, named like the Python class (`WiFi_Radio`,
`IP_Interface_IPv4Address`); an optional property per parameter; a child
object as a property of its interface type; a table as `Instances<Child>`,
a record keyed by instance number; and a template literal index signature
that admits `X_` vendor members, so a misspelt standard name is still an
error:

```
error TS2561: 'Channle' does not exist in type 'WiFi_Radio'. Did you mean to write 'Channel'?
```

| Base type | TypeScript |
| --- | --- |
| `string` | `string`, or `Open<"a" \| "b">` for a closed enumeration |
| `int`, `unsignedInt`, `long`, `unsignedLong`, `decimal` | `number` |
| `boolean` | `boolean` |
| `dateTime`, `hexBinary`, `base64` | `string` |
| any list | `T[]` |

`Open<T>` is `T | (string & {})`: the editor completes the Forum's values
and any other string still type checks, the same trade the Python models
make. The declarations are emitted from the IR directly rather than
converted from the JSON Schema, which would close the union.

Descriptions become doc comments on every interface and property, so an
editor shows the Forum's text on hover; `--no-descriptions` leaves them
out. The root of the model is `Root`, `Instances<VoiceService>` for a
service model. `Commands` maps every command path to its input and output
interfaces and `Events` every event path to its payload.

## Published declarations

Every release attaches the declarations of each shipped package to the
GitHub release as `<package>.d.ts`, beside the JSON Schemas.
