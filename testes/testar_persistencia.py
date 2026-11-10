"""Persistência do menu: gravação atômica, arquivo corrompido nunca vira
padrão em silêncio, edição feita por fora é enxergada, cache não relê à toa."""
import json
import os

from iris.core import app_launcher, armazenamento, radial_menu


def _config(tmp):
    return tmp / "menu_radial_config.json"


def testar_primeira_carga_cria_padrao(dados_isolados):
    tmp, avisos = dados_isolados
    assert radial_menu.obter_favoritos() == radial_menu.FAVORITOS_PADRAO
    assert _config(tmp).exists()
    assert avisos == []


def testar_arquivo_corrompido_restaura_backup_e_guarda_o_ruim(dados_isolados):
    tmp, avisos = dados_isolados
    radial_menu.salvar_favoritos(["calculadora"])
    radial_menu.salvar_favoritos(["calculadora", "youtube"])  # .bak = estado anterior
    _config(tmp).write_text('{"perfis": {"Geral": {"favor', encoding="utf-8")

    assert radial_menu.obter_favoritos() == ["calculadora"]
    guardados = [n for n in os.listdir(tmp) if ".corrompido-" in n]
    assert len(guardados) == 1
    assert len(avisos) == 1 and "corrompida" in avisos[0]


def testar_corrompido_sem_backup_recomeca_mas_nao_apaga(dados_isolados):
    tmp, avisos = dados_isolados
    _config(tmp).write_text("isto não é json", encoding="utf-8")

    assert radial_menu.obter_favoritos() == radial_menu.FAVORITOS_PADRAO
    guardado = [n for n in os.listdir(tmp) if ".corrompido-" in n][0]
    assert (tmp / guardado).read_text(encoding="utf-8") == "isto não é json"
    assert len(avisos) == 1


def testar_edicao_por_fora_nao_e_perdida(dados_isolados):
    """A regressão de 2026-09-06: editar o JSON com o IRIS rodando e a
    edição sumir na gravação seguinte."""
    tmp, _ = dados_isolados
    radial_menu.salvar_favoritos(["calculadora"])
    dados = json.loads(_config(tmp).read_text(encoding="utf-8"))
    dados["pastas"]["Externa"] = {"caminho": "C:/x", "ativa": True}
    _config(tmp).write_text(json.dumps(dados) + " ", encoding="utf-8")  # tamanho muda

    radial_menu.registrar_uso("calculadora")  # uma gravação qualquer

    assert "Externa" in radial_menu.obter_pastas_todas()
    assert json.loads(_config(tmp).read_text(encoding="utf-8"))["pastas"]["Externa"]["caminho"] == "C:/x"


def testar_leituras_repetidas_nao_releem_o_arquivo(dados_isolados, monkeypatch):
    radial_menu.obter_favoritos()
    leituras = []
    original = armazenamento.ler_json
    monkeypatch.setattr(armazenamento, "ler_json", lambda c: leituras.append(c) or original(c))
    for _ in range(50):
        radial_menu.obter_categorias()
        radial_menu.obter_apelido("x")
        radial_menu.obter_icone_customizado("x")
    assert leituras == []


def testar_gravacao_nao_deixa_temporario(dados_isolados):
    tmp, _ = dados_isolados
    radial_menu.salvar_favoritos(["a"])
    radial_menu.salvar_favoritos(["a", "b"])
    nomes = set(os.listdir(tmp))
    assert "menu_radial_config.json.tmp" not in nomes
    assert "menu_radial_config.json.bak" in nomes


def testar_migracao_de_formatos_antigos(dados_isolados):
    tmp, _ = dados_isolados
    _config(tmp).write_text(json.dumps({
        "perfil_atual": "Geral",
        "perfis": {"Geral": {"favoritos": ["🎬 Anime Tracker"], "categorias": {}, "uso": {"🎬 Anime Tracker": 3}}},
        "pastas": {"Docs": "C:/docs"},
        "limite_por_camada": 10,
    }), encoding="utf-8")

    assert radial_menu.obter_favoritos() == ["🎬 Watchlist"]
    assert radial_menu.obter_contagem_uso() == {"🎬 Watchlist": 3}
    assert radial_menu.obter_pastas() == {"Docs": "C:/docs"}
    assert radial_menu.obter_limite_por_camada_favoritos() == 10
    assert radial_menu.obter_limite_por_camada_subitens() == 10


def testar_perfis_apelidos_e_recentes(dados_isolados):
    radial_menu.salvar_favoritos(["a", "b"])
    radial_menu.criar_perfil("Trabalho", copiar_de="Geral")
    radial_menu.definir_perfil_atual("Trabalho")
    radial_menu.salvar_favoritos(["c"])
    assert radial_menu.obter_favoritos("Geral") == ["a", "b"]
    radial_menu.renomear_perfil("Trabalho", "Foco")
    assert radial_menu.obter_perfil_atual() == "Foco"
    radial_menu.remover_perfil("Foco")
    assert radial_menu.obter_nomes_perfis() == ["Geral"]
    radial_menu.remover_perfil("Geral")  # nunca fica sem perfil
    assert radial_menu.obter_nomes_perfis() == ["Geral"]

    radial_menu.definir_apelido("a", "Alfa")
    radial_menu.definir_icone_customizado("a", "⭐")
    assert radial_menu.obter_personalizacoes() == {"a": {"apelido": "Alfa", "icone": "⭐"}}

    for nome in ["1", "2", "3", "4", "5", "6", "7", "1"]:
        radial_menu.registrar_recente(nome)
    assert radial_menu.obter_recentes() == ["1", "7", "6", "5", "4", "3"]


def testar_apps_manuais_ilegiveis_nao_sao_sobrescritos(dados_isolados):
    tmp, _ = dados_isolados
    app_launcher.adicionar_app_manual("Meu App", "C:/x/app.exe")
    (tmp / "apps_manuais.json").write_text("{quebrado", encoding="utf-8")

    assert app_launcher.listar_apps_manuais() == {}  # leitura tolera
    try:
        app_launcher.adicionar_app_manual("Outro", "C:/y.exe")  # gravação não
    except armazenamento.ArquivoIlegivel:
        pass
    else:
        raise AssertionError("gravar por cima de arquivo ilegível deveria falhar")
    assert (tmp / "apps_manuais.json").read_text(encoding="utf-8") == "{quebrado"


def testar_busca_exata_nao_abre_app_parecido(dados_isolados):
    launcher = app_launcher.AppLauncher()
    assert launcher.find_app("calculadora", exato=True)[0] == "calculadora"
    assert launcher.find_app("notas", exato=True)[0] == "bloco de notas"  # apelido idêntico vale
    assert launcher.find_app("abrir de notas", exato=True) == (None, None)
    assert launcher.find_app("abrir de notas")[0] == "bloco de notas"  # texto livre continua aproximado


def testar_leitura_em_lote_confere_o_disco_uma_vez(dados_isolados, monkeypatch):
    radial_menu.obter_favoritos()
    consultas = []
    original = radial_menu._assinatura_arquivo
    monkeypatch.setattr(radial_menu, "_assinatura_arquivo", lambda: consultas.append(1) or original())
    with radial_menu.leitura_em_lote():
        for _ in range(40):
            radial_menu.obter_apelido("x")
            radial_menu.obter_categorias()
    assert len(consultas) == 1
    radial_menu.obter_apelido("x")
    assert len(consultas) == 2  # fora do bloco volta a conferir
