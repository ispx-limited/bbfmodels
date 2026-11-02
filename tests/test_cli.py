import json
from pathlib import Path

import pytest

from bbfmodels import __version__
from bbfmodels.cli import main

FIXTURE = Path(__file__).parent / "fixtures" / "mini-cwmp-full.xml"


def test_version_is_a_string() -> None:
    assert isinstance(__version__, str)
    assert __version__


def test_help_runs(capsys: pytest.CaptureFixture[str]) -> None:
    assert main([]) == 0
    assert "Broadband Forum" in capsys.readouterr().out


def test_ir_writes_json(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    out = tmp_path / "mini.json"
    assert main(["ir", str(FIXTURE), "-o", str(out), "--indent", "2"]) == 0
    doc = json.loads(out.read_text())
    assert doc["spec"] == "urn:example-org:mini-1-0-0-cwmp"
    assert "Device.Radio.{i}." in doc["models"][0]["objects"]
    assert main(["ir", str(FIXTURE)]) == 0
    assert json.loads(capsys.readouterr().out)["protocol"] == "cwmp"


def test_ir_reports_a_bad_document(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    bad = tmp_path / "bad.xml"
    bad.write_text("<model/>")
    assert main(["ir", str(bad)]) == 1
    assert "expected <document>" in capsys.readouterr().err
    assert main(["ir", str(tmp_path / "missing.xml")]) == 1


def test_ir_schema_is_json_schema(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["ir-schema"]) == 0
    schema = json.loads(capsys.readouterr().out)
    assert schema["title"] == "Document"
    assert "Object" in schema["$defs"]
