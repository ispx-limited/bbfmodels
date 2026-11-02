# 0011: Typed paths are a generic runtime plus a stub, not generated classes

## Context

Not every user wants models. Code that queries an ACS API asks for a
parameter by its path string and gets a string back, and what it needs
from bbfmodels is a correct path with autocomplete and the parameter's
definition one step away. Generating a class per object with a property
per member would give that, at the cost of another megabyte of code per
package, import time to match, and a second copy of every name the models
already carry.

## Decision

Typed paths are one generic runtime (`bbfmodels.paths`) that walks the
package's shipped IR, plus a generated stub file (`paths.pyi`) per package
that declares every object and parameter with the Python type of its
value. The runtime `paths.py` in a package is three lines: the root path
over the package's schema. Editors and type checkers read the stub; the
interpreter never does.

- `str()` of a path is the data path. A table renders as its partial path
  and offers `search` for the USP wildcard form and `schema_path` for the
  `{i}` form. Paths compare and hash as strings.
- `definition` returns the IR object or parameter.
- An unknown name is an `AttributeError`. A name the schema does not list
  is reached with `child()`, so a typo in a standard name is never taken
  for a vendor parameter.
- Identifiers follow the models' rule (`N11kEnable` for `11kEnable`), and
  the runtime maps the identifier back to the Forum name.

pydantic remains a dependency even for a user who only wants paths, because
the IR the runtime walks is built on it. That is accepted: the cost is one
ubiquitous package, and a second dependency-free distribution can be split
out if someone needs it.

## Consequences

- Autocomplete over the whole of TR-181 with no import cost: the stub for
  TR-181 is a few hundred kilobytes that only tools read.
- The first attribute access loads the package's IR (about 50 ms); every
  one after that is a dictionary lookup.
- The value type in the stub (`ParamPath[int]`) is documentation for the
  reader and the type checker; the runtime does not use it.
