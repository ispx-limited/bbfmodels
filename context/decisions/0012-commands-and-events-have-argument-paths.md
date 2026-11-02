# 0012: Commands and events get argument paths, and classes named by owner

## Context

USP adds commands (`Device.Reboot()`, `Device.IP.Diagnostics.TraceRoute()`)
with input and output arguments, and events (`Device.Boot!`) with a
payload. The specification gives the command and the event a path but not
their arguments: an Operate request carries input arguments as a map of
names to values, and the response the output the same way, with objects
inside an output (`RouteHops.{i}.`) flattened into dotted names. The
schema, the models and the paths each needed a way to refer to those
arguments, and command names repeat across objects (`Reset()`,
`Upload()`, `ScheduleTimer()`), so a class cannot be named after the
command alone.

## Decision

- **The schema indexes arguments as objects under synthetic paths**:
  `Device.IP.Diagnostics.TraceRoute().Input.`,
  `Device.IP.Diagnostics.TraceRoute().Output.`, `Device.Boot!.`, with the
  objects inside an output under them
  (`...TraceRoute().Output.RouteHops.{i}.`). Argument values then resolve
  and validate like any parameter. These objects are not `children()` of
  the owning object; they are reached through the command or event.
- **Generated classes are named by owner, command and side**:
  `IP_Diagnostics_TraceRoute_Input`, `IP_Diagnostics_TraceRoute_Output`,
  `IP_Diagnostics_TraceRoute_Output_RouteHops`; an event is `Device_Boot_Event`, the suffix keeping it apart from an object class of the same name.
  Each package exposes `COMMANDS`, a map from command path to its input
  and output classes, and `EVENTS`, from event path to its class, so a
  controller can pick the class for a response by the path it sent.
  `flatten("")` gives the bare argument names an Operate request carries.
- **Paths name commands and events as the specification does**:
  `str(Device.IP.Diagnostics.TraceRoute)` is `Device.IP.Diagnostics.TraceRoute()`
  and `str(Device.Boot)` is `Device.Boot!`; attribute access drops the
  suffix, `child()` takes the full name.
- **`codec.xsd_type` gives the `xsi:type` CWMP carries** for a parameter,
  derived from its base type, `xsd:string` for any list. This is the one
  piece a CWMP stack needs from the model that the model alone did not
  state. SOAP and protobuf envelopes stay out of scope.

## Consequences

- The synthetic paths are bbfmodels' own notation and never appear on the
  wire; they exist so that one validation routine serves parameters and
  arguments alike.
- TR-181 USP generates 1486 classes rather than 975; import time is
  unchanged at about a third of a second.
