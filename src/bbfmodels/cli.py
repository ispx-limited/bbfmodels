"""Command line entry point."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from bbfmodels import __version__, sources
from bbfmodels.ir import Document
from bbfmodels.parser import ParseError, parse_file


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="bbfmodels",
        description="Typed models and schema tooling for Broadband Forum data models.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command")

    fetch = sub.add_parser("fetch", help="download published documents into the local cache")
    fetch.add_argument("names", nargs="*", help="document file names; none means the core set")
    fetch.add_argument(
        "--list", choices=sorted(sources.SITES), help="list what the Forum publishes"
    )
    fetch.add_argument("--into", type=Path, help="directory to download into")

    ir = sub.add_parser("ir", help="parse a document and write its IR as JSON")
    ir.add_argument("document", type=Path)
    ir.add_argument("-o", "--output", type=Path, help="write here instead of stdout")
    ir.add_argument("--indent", type=int, default=None, help="pretty-print with this indent")

    sub.add_parser("ir-schema", help="print the JSON Schema of the IR")

    js = sub.add_parser("jsonschema", help="write the JSON Schema of a document's model")
    js.add_argument("document", type=Path)
    js.add_argument("-o", "--output", type=Path, help="write here instead of stdout")
    js.add_argument("--indent", type=int, default=None, help="pretty-print with this indent")
    js.add_argument("--lenient", action="store_true", help="types only, no facet constraints")
    js.add_argument(
        "--no-descriptions", action="store_true", help="leave the Forum's descriptions out"
    )

    gen = sub.add_parser("generate", help="generate a package of pydantic models from a document")
    gen.add_argument(
        "document", type=Path, nargs="?", help="a document; none means every shipped package"
    )
    gen.add_argument("--package", help="dotted package name, for example vendor.models")
    gen.add_argument("--root", type=Path, default=Path("src"), help="source root to write under")

    ts = sub.add_parser(
        "typescript", help="write the TypeScript declarations of a document's model"
    )
    ts.add_argument("document", type=Path)
    ts.add_argument("-o", "--output", type=Path, help="write here instead of stdout")
    ts.add_argument(
        "--no-descriptions", action="store_true", help="leave the Forum's descriptions out"
    )

    go = sub.add_parser("go", help="write the Go types of a document's model into a directory")
    go.add_argument("document", type=Path)
    go.add_argument("--package", required=True, help="Go package name, for example tr181cwmp")
    go.add_argument("-o", "--output", type=Path, required=True, help="directory to write into")
    go.add_argument(
        "--no-descriptions", action="store_true", help="leave the Forum's descriptions out"
    )

    dist = sub.add_parser(
        "distribute", help="assemble the Go module or the npm package of every shipped model"
    )
    dist.add_argument("kind", choices=["go", "npm"])
    dist.add_argument("-o", "--output", type=Path, required=True, help="directory to write into")
    dist.add_argument("--stamp", default=None, help="version to stamp; default is bbfmodels' own")

    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0
    try:
        if args.command == "fetch":
            return _fetch(args)
        if args.command == "ir":
            return _ir(args)
        if args.command == "ir-schema":
            print(json.dumps(Document.model_json_schema(), indent=2))
            return 0
        if args.command == "generate":
            return _generate(args)
        if args.command == "jsonschema":
            return _jsonschema(args)
        if args.command == "typescript":
            return _typescript(args)
        if args.command == "go":
            return _go(args)
        if args.command == "distribute":
            return _distribute(args)
    except ParseError as exc:
        print(f"bbfmodels: {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"bbfmodels: {exc}", file=sys.stderr)
        return 1
    return 2


def _fetch(args: argparse.Namespace) -> int:
    if args.list:
        for name in sources.available(args.list):
            print(name)
        return 0
    for name in args.names or sources.CORE:
        print(sources.fetch(name, args.into))
    return 0


def _generate(args: argparse.Namespace) -> int:
    from bbfmodels import generate

    if args.document is None:
        for package, name in generate.PACKAGES.items():
            for path in generate.write_package(package, sources.fetch(name), args.root):
                print(path)
        return 0
    if not args.package:
        print("bbfmodels: --package is required with a document", file=sys.stderr)
        return 2
    for path in generate.write_package(args.package, args.document, args.root):
        print(path)
    return 0


def _jsonschema(args: argparse.Namespace) -> int:
    from bbfmodels.jsonschema import document_schema

    schema = document_schema(
        parse_file(args.document), lenient=args.lenient, descriptions=not args.no_descriptions
    )
    text = json.dumps(schema, indent=args.indent, ensure_ascii=False)
    if args.output:
        args.output.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0


def _typescript(args: argparse.Namespace) -> int:
    from bbfmodels.typescript import declarations

    text = declarations(parse_file(args.document), descriptions=not args.no_descriptions)
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


def _go(args: argparse.Namespace) -> int:
    from bbfmodels.golang import write_go_package

    paths = write_go_package(
        parse_file(args.document), args.package, args.output, descriptions=not args.no_descriptions
    )
    for path in paths:
        print(path)
    return 0


def _distribute(args: argparse.Namespace) -> int:
    from bbfmodels import distribute

    build = distribute.go_module if args.kind == "go" else distribute.npm_package
    for path in build(args.output, args.stamp or __version__):
        print(path)
    return 0


def _ir(args: argparse.Namespace) -> int:
    doc = parse_file(args.document)
    text = doc.model_dump_json(exclude_defaults=True, indent=args.indent)
    if args.output:
        args.output.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
