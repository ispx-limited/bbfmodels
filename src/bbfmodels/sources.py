"""Fetch published data model documents from the Forum.

The Forum serves every published flattened document from two static sites,
one per protocol. A file is named
``tr-<number>-<issue>-<amendment>-<corrigendum>[-cwmp|-usp]-full.xml`` and
never changes once published, so a downloaded copy is kept in a local cache
and reused.
"""

from __future__ import annotations

import os
import re
import urllib.request
from pathlib import Path

SITES = {
    "cwmp": "https://cwmp-data-models.broadband-forum.org/",
    "usp": "https://usp-data-models.broadband-forum.org/",
}

# The documents the test suite and the shipped models are generated from.
# Moving one is a deliberate change: the generated output moves with it.
CORE = (
    "tr-098-1-8-0-full.xml",
    "tr-104-1-1-0-full.xml",
    "tr-104-2-0-2-cwmp-full.xml",
    "tr-104-2-0-2-usp-full.xml",
    "tr-135-1-4-1-cwmp-full.xml",
    "tr-135-1-4-1-usp-full.xml",
    "tr-140-1-3-1-cwmp-full.xml",
    "tr-140-1-3-1-usp-full.xml",
    "tr-157-1-3-0-full.xml",
    "tr-181-2-21-0-cwmp-full.xml",
    "tr-181-2-21-0-usp-full.xml",
)

_FILE = re.compile(r"^tr-\d+-\d+-\d+-\d+(?:-(cwmp|usp))?-full\.xml$")
_HREF = re.compile(r'href="(tr-\d+-\d+-\d+-\d+(?:-(?:cwmp|usp))?-full\.xml)"')


def cache_dir() -> Path:
    """Where fetched documents live: ``$BBFMODELS_CACHE``, else the XDG cache."""
    env = os.environ.get("BBFMODELS_CACHE")
    if env:
        return Path(env)
    xdg = os.environ.get("XDG_CACHE_HOME") or str(Path.home() / ".cache")
    return Path(xdg) / "bbfmodels"


def site_for(name: str) -> str:
    """The site a document is published on, from its name."""
    m = _FILE.match(name)
    if not m:
        raise ValueError(f"{name!r} is not a published document name")
    # Documents without a protocol suffix predate USP and live on the CWMP site.
    return SITES["usp"] if m.group(1) == "usp" else SITES["cwmp"]


def available(protocol: str) -> list[str]:
    """Every flattened document the Forum lists for a protocol."""
    with urllib.request.urlopen(SITES[protocol], timeout=30) as resp:
        index = resp.read().decode("utf-8", errors="replace")
    return sorted(set(_HREF.findall(index)))


def fetch(name: str, into: Path | None = None) -> Path:
    """Return the local copy of a document, downloading it if needed."""
    target = (into or cache_dir()) / name
    if target.exists():
        return target
    url = site_for(name) + name
    target.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url, timeout=60) as resp:
        data = resp.read()
    tmp = target.with_suffix(".part")
    tmp.write_bytes(data)
    tmp.replace(target)
    return target
