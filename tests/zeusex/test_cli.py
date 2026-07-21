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


def test_marketplace_analyze360_outputs_json() -> None:
    payload = (
        '{"product":{"name":"Produto","marketplace":"shopee",'
        '"sale_price":"100","product_cost":"40"},'
        '"attributes":{"Material":"mandioca"}}'
    )
    result = CliRunner().invoke(
        zeusex,
        [
            "marketplace",
            "analyze360",
            "--payload",
            payload,
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 0
    assert '"profit"' in result.output
    assert '"advertisement"' in result.output
    assert '"Material: mandioca"' in result.output


def test_marketplace_analyze360_can_save_and_rank(tmp_path) -> None:
    payload = (
        '{"product":{"name":"Produto promissor","marketplace":"shopee",'
        '"sale_price":"100","product_cost":"40"},'
        '"signals":{"demand":"90","competition":"20","margin":"80",'
        '"listing_quality":"80"}}'
    )
    env = {"ZEUSEX_DATA_DIR": str(tmp_path)}
    runner = CliRunner()

    saved = runner.invoke(
        zeusex,
        [
            "marketplace",
            "analyze360",
            "--payload",
            payload,
            "--format",
            "json",
            "--save",
        ],
        env=env,
    )
    ranked = runner.invoke(
        zeusex,
        ["marketplace", "reports", "top"],
        env=env,
    )
    shown = runner.invoke(
        zeusex,
        ["marketplace", "reports", "show", "1", "--format", "markdown"],
        env=env,
    )

    assert saved.exit_code == 0
    assert "Relatório salvo com ID 1" in saved.output
    assert ranked.exit_code == 0
    assert "Produto promissor" in ranked.output
    assert shown.exit_code == 0
    assert "# Análise 360" in shown.output


def test_marketplace_content_generates_all_channels() -> None:
    payload = (
        '{"product":{"name":"Areia biodegradável","marketplace":"shopee",'
        '"sale_price":"49.90","product_cost":"25"},'
        '"attributes":{"Material":"mandioca","Peso":"4 kg"}}'
    )
    result = CliRunner().invoke(
        zeusex,
        [
            "marketplace",
            "content",
            "--payload",
            payload,
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 0
    assert '"shopee"' in result.output
    assert '"mercado_livre"' in result.output
    assert '"whatsapp"' in result.output
    assert '"instagram"' in result.output
    assert '"duration_seconds": 60' in result.output
    assert "Material: mandioca" in result.output


def test_achadinhos_jr_campaign_includes_safe_combinations() -> None:
    payload = (
        '{"product":{"name":"Areia","marketplace":"shopee",'
        '"sale_price":"49.90","product_cost":"25"},'
        '"attributes":{"Material":"mandioca"},'
        '"catalog":['
        '{"name":"Areia","category":"higiene","price":"49.90",'
        '"kit_group":"limpeza","complements":["Pá"]},'
        '{"name":"Pá","category":"higiene","price":"59.90",'
        '"kit_group":"limpeza"}]}'
    )
    result = CliRunner().invoke(
        zeusex,
        [
            "marketplace",
            "campaign",
            "--preset",
            "achadinhos-jr",
            "--payload",
            payload,
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 0
    assert "Achadinhos do JR" in result.output
    assert '"kind": "kit"' in result.output
    assert '"kind": "upsell"' in result.output
    assert '"kind": "cross_sell"' in result.output
    assert "Material: mandioca" in result.output
