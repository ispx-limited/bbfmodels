# 0009: The data tree keeps wire text and decodes on demand

## Context

A tree built from a device's values has two jobs that pull in different
directions: give the caller typed values (an `int` channel, a `bool`
enable, a `list` of standards) and write the values back out exactly as
they came in. Decoding on the way in and encoding on the way out does not
round-trip: `1` becomes `true`, `a, b` becomes `a,b`, `888e` becomes
`888E`. All are the same value, and all would show up as a change in a
diff, a comparison against a previous read, or a set sent back to the
device.

## Decision

`Node` stores the wire text of every parameter as received. `value()`
decodes through the parameter's syntax when asked, `set()` encodes a
Python value to text once, and `flatten()` returns the stored text. A
parameter the schema does not define has text only; it is kept and
returned unchanged, and `set()` accepts text for it.

Children and tables are kept in the order they were first seen, so a tree
flattens in the order it was built from.

## Consequences

- `Tree.from_flat(...).flatten()` returns its input, key order included,
  and the test suite asserts it.
- Decoding cost is paid per read, not per build. Building a tree from a
  full device export is a dictionary walk.
- Validation is explicit: `Tree.problems()` checks every known parameter's
  text against its facets. Storing text means an out-of-range value from a
  device is held and reported, not rejected on the way in.
