from openjarvis.zeusex import ZEUSEX_IDENTITY, ZeusExIdentity


def test_default_identity() -> None:
    assert ZEUSEX_IDENTITY.name == "ZeusExAI"
    assert ZEUSEX_IDENTITY.short_name == "Zeus"
    assert ZEUSEX_IDENTITY.locale == "pt-BR"
    assert ZEUSEX_IDENTITY.wake_word == "Zeus"


def test_sales_mode_prompt_contains_marketplaces_and_confirmation() -> None:
    prompt = ZEUSEX_IDENTITY.system_prompt("sales")

    assert "Shopee" in prompt
    assert "Mercado Livre" in prompt
    assert "solicite confirmação explícita" in prompt
    assert "Não invente resultados" in prompt


def test_unknown_mode_falls_back_to_assistant_purpose() -> None:
    identity = ZeusExIdentity()
    prompt = identity.system_prompt("modo-inexistente")

    assert "conversa, pesquisa, organização e apoio geral" in prompt
