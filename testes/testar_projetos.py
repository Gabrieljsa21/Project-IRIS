"""Categoria Projects: descoberta por convenção e sincronização que só
acrescenta o que é novo."""
from iris.core import app_launcher, radial_menu


def _criar_projetos(raiz, icones=None):
    (raiz / "Project-ARGUS").mkdir()
    (raiz / "Project-ARGUS" / "iniciar_argus_oculto.vbs").write_text("")
    (raiz / "Project G.A.I.A" / "assistant").mkdir(parents=True)
    (raiz / "Project G.A.I.A" / "assistant" / "iniciar_galateia_oculto.vbs").write_text("")
    (raiz / "Project-HERMES").mkdir()
    (raiz / "Project-HERMES" / "iniciar_hermes.bat").write_text("")
    (raiz / "Project-HERMES" / "iniciar_hermes_debug.bat").write_text("")
    (raiz / "Project-MIDAS").mkdir()
    (raiz / "Project-MIDAS" / "MIDAS.bat").write_text("")
    (raiz / "Project-PANDORA").mkdir()
    (raiz / "Projetos soltos").mkdir()
    (raiz / "Projectile").mkdir()
    if icones:
        icones.mkdir()
        (icones / "Argus.png").write_bytes(b"png")


def testar_descoberta_por_convencao(dados_isolados, tmp_path_factory):
    raiz = tmp_path_factory.mktemp("workspace")
    icones = raiz / "icones"
    _criar_projetos(raiz, icones)

    projetos = {p["nome"]: p for p in radial_menu.descobrir_projetos(str(raiz), str(icones))}

    assert sorted(projetos) == ["ARGUS", "GAIA", "HERMES", "MIDAS", "PANDORA"]
    assert projetos["ARGUS"]["inicializador"].endswith("iniciar_argus_oculto.vbs")
    assert projetos["GAIA"]["inicializador"].endswith("iniciar_galateia_oculto.vbs")
    assert projetos["HERMES"]["inicializador"].endswith("iniciar_hermes.bat")
    assert projetos["MIDAS"]["inicializador"].endswith("MIDAS.bat")
    assert projetos["PANDORA"]["inicializador"] is None
    assert projetos["ARGUS"]["icone"].endswith("Argus.png")
    assert projetos["GAIA"]["icone"] is None


def testar_primeira_sincronizacao_cria_categoria(dados_isolados, tmp_path_factory):
    raiz = tmp_path_factory.mktemp("workspace")
    _criar_projetos(raiz)
    radial_menu.salvar_pasta_projetos(str(raiz))

    adicionados = radial_menu.sincronizar_categoria_projetos()

    assert sorted(adicionados) == ["ARGUS", "GAIA", "HERMES", "MIDAS", "PANDORA"]
    itens = radial_menu.obter_categorias()["Projects"]["itens"]
    assert "ARGUS" in itens and "📁 PANDORA" in itens
    assert "Projects" in radial_menu.obter_favoritos()
    assert "argus" in app_launcher.listar_apps_manuais()
    assert radial_menu.sincronizar_categoria_projetos() == []  # idempotente


def testar_item_removido_nao_volta_e_projeto_novo_entra(dados_isolados, tmp_path_factory):
    raiz = tmp_path_factory.mktemp("workspace")
    _criar_projetos(raiz)
    radial_menu.salvar_pasta_projetos(str(raiz))
    radial_menu.sincronizar_categoria_projetos()

    itens = [i for i in radial_menu.obter_categorias()["Projects"]["itens"] if i != "MIDAS"]
    radial_menu.salvar_categoria("Projects", itens)
    (raiz / "Project-CHRONOS").mkdir()

    assert radial_menu.sincronizar_categoria_projetos() == ["CHRONOS"]
    itens = radial_menu.obter_categorias()["Projects"]["itens"]
    assert "MIDAS" not in itens and "📁 CHRONOS" in itens


def testar_categoria_apagada_nao_e_recriada(dados_isolados, tmp_path_factory):
    raiz = tmp_path_factory.mktemp("workspace")
    _criar_projetos(raiz)
    radial_menu.salvar_pasta_projetos(str(raiz))
    radial_menu.sincronizar_categoria_projetos()
    radial_menu.remover_categoria("Projects")
    (raiz / "Project-CHRONOS").mkdir()

    assert radial_menu.sincronizar_categoria_projetos() == []
    assert "Projects" not in radial_menu.obter_categorias()


def testar_migracao_do_seed_antigo(dados_isolados, tmp_path_factory):
    """Config da 0.3.0: categoria criada pelo seed fixo, sem a lista de
    conhecidos. O que já está lá não duplica; só entra o que é novo."""
    raiz = tmp_path_factory.mktemp("workspace")
    _criar_projetos(raiz)
    radial_menu.salvar_categoria("Projects", ["GAIA", "ARGUS", "📁 PANDORA"])
    dados = radial_menu._carregar()
    dados["categoria_projetos_criada_v2"] = True
    dados["pasta_projetos"] = str(raiz)
    radial_menu._salvar(dados)

    assert sorted(radial_menu.sincronizar_categoria_projetos()) == ["HERMES", "MIDAS"]
    assert radial_menu.obter_categorias()["Projects"]["itens"] == ["GAIA", "ARGUS", "📁 PANDORA", "HERMES", "MIDAS"]
