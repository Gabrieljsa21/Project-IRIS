"""Geometria do popup, atalho e busca - funções puras, sem Qt."""
import math

import pytest

from iris.core.atalho import MOD_ALT, MOD_CONTROL, MOD_SHIFT, MOD_WIN, AtalhoInvalido, descrever_atalho, interpretar_atalho
from iris.ui import geometria_radial as g


def _ponto(angulo_graus, raio):
    """Coordenadas de tela (y pra baixo) relativas ao centro."""
    rad = math.radians(angulo_graus)
    return raio * math.cos(rad), -raio * math.sin(rad)


def testar_item_zero_no_topo_e_sentido_horario():
    assert g.angulo_item(0, 8) == 90
    assert g.angulo_item(2, 8) == 0      # 3h
    assert g.angulo_item(4, 8) == 270    # 6h


def testar_clique_acerta_a_fatia_desenhada():
    raio = (g.RAIO_INTERNO + g.RAIO_EXTERNO_1) / 2
    for capacidade in (3, 8, 13, 24):
        for indice in range(capacidade):
            dx, dy = _ponto(g.angulo_item(indice, capacidade), raio)
            assert g.fatia_no_anel(dx, dy, g.RAIO_INTERNO, g.RAIO_EXTERNO_1, capacidade, capacidade) == indice


def testar_fora_do_anel_ou_posicao_vazia_nao_acerta():
    raio = (g.RAIO_INTERNO + g.RAIO_EXTERNO_1) / 2
    assert g.fatia_no_anel(0, -10, g.RAIO_INTERNO, g.RAIO_EXTERNO_1, 8, 8) is None       # centro
    assert g.fatia_no_anel(0, -500, g.RAIO_INTERNO, g.RAIO_EXTERNO_1, 8, 8) is None      # além da borda
    dx, dy = _ponto(g.angulo_item(5, 8), raio)
    assert g.fatia_no_anel(dx, dy, g.RAIO_INTERNO, g.RAIO_EXTERNO_1, 8, 3) is None       # só 3 itens


def testar_anel_aninhado_segue_a_referencia():
    r_int, r_ext = g.raio_interno_nivel(1), g.raio_externo_nivel(1)
    dx, dy = _ponto(g.angulo_item(1, 8, referencia=200.0), (r_int + r_ext) / 2)
    assert g.fatia_no_anel(dx, dy, r_int, r_ext, 8, 4, referencia=200.0) == 1


def testar_raios_crescem_sem_sobrepor():
    for nivel in range(1, g.MAX_NIVEIS_ANINHADOS):
        assert g.raio_interno_nivel(nivel) == g.raio_externo_nivel(nivel - 1) + g.GAP_ENTRE_ANEIS
    assert g.tamanho_para_profundidade(1) > g.tamanho_para_profundidade(0)


def testar_margem_recua_quando_nao_cabe():
    assert g.margem_ancora_que_cabe(4000, 3) == g.tamanho_para_profundidade(3) // 2
    assert g.margem_ancora_que_cabe(600, 3) == g.tamanho_para_profundidade(0) // 2


def testar_paginacao():
    assert g.paginar([1, 2, 3], 0, 8) == ([1, 2, 3], 0, 1)
    itens = list(range(10))
    pagina, indice, total = g.paginar(itens, 0, 4)
    assert pagina == [0, 1, 2, g.ITEM_MAIS_PAGINA] and (indice, total) == (0, 4)
    assert g.paginar(itens, 3, 4)[0] == [9, g.ITEM_MAIS_PAGINA]
    assert g.paginar(itens, 4, 4)[1] == 0     # avança além da última: volta à primeira
    assert g.paginar(itens, -1, 4)[1] == 3    # roda do mouse pra trás


def testar_dividir_icone_rotulo():
    assert g.dividir_icone_rotulo("📁 Jogos") == ("📁", "Jogos")
    assert g.dividir_icone_rotulo("bloco de notas") == (None, "bloco de notas")
    assert g.dividir_icone_rotulo("🎮") == ("🎮", "")


def testar_busca_ignora_acento_e_maiusculas():
    assert g.corresponde_busca("calculo", "Cálculo Rápido")
    assert g.corresponde_busca("ÁUDIO", "configuração de audio")
    assert g.corresponde_busca("pokemon", None, "Pokémon Legends")
    assert not g.corresponde_busca("xyz", "calculadora", None)


def testar_atalho_tolerante_e_canonico():
    assert interpretar_atalho("ctrl+alt+space") == (MOD_CONTROL | MOD_ALT, 0x20, "ctrl+alt+space")
    assert interpretar_atalho(" Alt + CTRL + Espaço ")[2] == "ctrl+alt+space"
    assert interpretar_atalho("win+shift+f12") == (MOD_WIN | MOD_SHIFT, 0x7B, "shift+win+f12")
    assert interpretar_atalho("Control+Q") == (MOD_CONTROL, ord("Q"), "ctrl+q")
    assert descrever_atalho("alt+ctrl+espaco") == "Ctrl+Alt+Espaço"


@pytest.mark.parametrize("texto", ["", "space", "ctrl+alt", "ctrl+a+b", "ctrl+tecla_inexistente", "ctrl+f25"])
def testar_atalho_invalido(texto):
    with pytest.raises(AtalhoInvalido):
        interpretar_atalho(texto)
