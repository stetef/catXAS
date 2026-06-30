"""Tests for the ``catxas`` command-line entry point."""

from click.testing import CliRunner

from catxas import cli


def test_cli_invokes_cleanly():
    result = CliRunner().invoke(cli.main)
    assert result.exit_code == 0


def test_cli_help():
    result = CliRunner().invoke(cli.main, ["--help"])
    assert result.exit_code == 0
    assert "--help" in result.output
