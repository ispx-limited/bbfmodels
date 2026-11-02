"""Command line entry point."""

import argparse
import sys

from bbfmodels import __version__


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="bbfmodels",
        description="Typed models and schema tooling for Broadband Forum data models.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.parse_args(argv)
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
