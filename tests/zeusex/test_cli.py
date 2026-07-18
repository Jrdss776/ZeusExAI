from click.testing import CliRunner

from openjarvis.cli.zeusex_cmd import zeusex


def test_status_command_shows_identity() -> None:
    result = CliRunner().invoke(zeusex, ["status", "--mode", "sales"])

    assert result.exit_code == 0
    assert "ZeusExAI" in result.output
    assert "pt-BR" in result.output
    assert "sales" in result.output


def test_prompt_command_uses_selected_mode() -> None:
    result = CliRunner().invoke(zeusex, ["prompt", "--mode", "developer"])

    assert result.exit_code == 0
    assert "Modo atual: developer" in result.output
    assert "GitHub" in result.output
