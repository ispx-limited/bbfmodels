from bbfmodels import __version__
from bbfmodels.cli import main


def test_version_is_a_string() -> None:
    assert isinstance(__version__, str)
    assert __version__


def test_help_runs(capsys) -> None:  # type: ignore[no-untyped-def]
    assert main([]) == 0
    assert "Broadband Forum" in capsys.readouterr().out
