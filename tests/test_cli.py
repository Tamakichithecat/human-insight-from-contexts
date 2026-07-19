from __future__ import annotations

from typer.testing import CliRunner

from hifc.cli.app import app


def test_cli_help():
    result = CliRunner().invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Human insight from contexts CLI" in result.stdout


def test_cli_doctor():
    result = CliRunner().invoke(app, ["doctor"])
    assert result.exit_code == 0
    assert "hifc foundation is installed" in result.stdout


def test_cli_version():
    result = CliRunner().invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.stdout
