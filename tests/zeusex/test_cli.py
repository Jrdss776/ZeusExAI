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


def test_marketplace_queue_add_and_list(tmp_path) -> None:
    runner = CliRunner()
    env = {"ZEUSEX_DATA_DIR": str(tmp_path)}

    added = runner.invoke(
        zeusex,
        [
            "marketplace",
            "queue",
            "add",
            "--marketplace",
            "mercado_livre",
            "--payload",
            '{"id":"MLB123"}',
        ],
        env=env,
    )
    listed = runner.invoke(
        zeusex,
        ["marketplace", "queue", "list"],
        env=env,
    )

    assert added.exit_code == 0
    assert "Trabalho 1 adicionado" in added.output
    assert listed.exit_code == 0
    assert "mercado_livre" in listed.output
    assert "queued" in listed.output


def test_marketplace_queue_rejects_non_object_json(tmp_path) -> None:
    result = CliRunner().invoke(
        zeusex,
        [
            "marketplace",
            "queue",
            "add",
            "--marketplace",
            "shopee",
            "--payload",
            '["não", "é", "objeto"]',
        ],
        env={"ZEUSEX_DATA_DIR": str(tmp_path)},
    )

    assert result.exit_code != 0
    assert "objeto JSON" in result.output
