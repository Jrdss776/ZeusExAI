from openjarvis.agents.james_master import JamesMasterAgent


def test_selects_graphic_design_specialist():
    name, instruction = JamesMasterAgent.select_specialist(
        "Crie um carrossel com identidade visual para o Instagram"
    )
    assert name == "design_grafico"
    assert "direcao de arte" in instruction


def test_routes_promotional_art_to_design_before_communication():
    name, _ = JamesMasterAgent.select_specialist(
        "Crie a arte de um anuncio promocional para redes sociais"
    )
    assert name == "design_grafico"


def test_selects_code_specialist():
    name, _ = JamesMasterAgent.select_specialist("Corrija este codigo Python")
    assert name == "codigo"


def test_selects_communication_specialist():
    name, _ = JamesMasterAgent.select_specialist("Escreva um e-mail ao cliente")
    assert name == "comunicacao"


def test_selects_research_specialist():
    name, _ = JamesMasterAgent.select_specialist("Pesquise dados e cite fontes")
    assert name == "pesquisa"


def test_falls_back_to_general_specialist():
    name, _ = JamesMasterAgent.select_specialist("Ola, tudo bem?")
    assert name == "geral"
