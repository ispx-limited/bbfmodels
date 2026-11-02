# Command line

```
bbfmodels fetch [NAME ...] [--list cwmp|usp] [--into DIR]
bbfmodels ir DOCUMENT [-o FILE] [--indent N]
bbfmodels ir-schema
bbfmodels generate [DOCUMENT --package NAME] [--root DIR]
bbfmodels jsonschema DOCUMENT [-o FILE] [--indent N] [--lenient] [--no-descriptions]
bbfmodels typescript DOCUMENT [-o FILE] [--no-descriptions]
bbfmodels go DOCUMENT --package NAME -o DIR [--no-descriptions]
bbfmodels --version
```

| Command | Does |
| --- | --- |
| `fetch` | Downloads published documents into the cache; no names means the core set. `--list` prints what the Forum publishes for a protocol. |
| `ir` | Parses a document and writes the IR as JSON, to stdout or `-o`. |
| `ir-schema` | Prints the JSON Schema of the IR. |
| `generate` | Writes a package of pydantic models from a document under `--root` (default `src`). With no document, regenerates every shipped package. |
| `jsonschema` | Writes the JSON Schema of a document's model. `--lenient` keeps types only; `--no-descriptions` leaves the Forum's prose out. |
| `typescript` | Writes the TypeScript declarations of a document's model. |
| `go` | Writes the Go types of a document's model into a directory, one file per subtree. |

The cache is `~/.cache/bbfmodels`, or `$XDG_CACHE_HOME/bbfmodels`, or
`$BBFMODELS_CACHE` when set.

Exit status is 0 on success, 1 when a document cannot be read or a file
cannot be written, with the reason on stderr, and 2 for a usage error.
