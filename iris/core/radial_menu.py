# -*- coding: utf-8 -*-
"""Menu Radial - persistência de dados (portado de `Project G.A.I.A/assistant/
features/radial_menu/radial_menu.py`, 2026-08 - ver `docs/ARQUITETURA.md` na raiz
do repo pro histórico da extração). Este módulo é só a PERSISTÊNCIA (dado
puro, sem nenhuma dependência de Qt) - a renderização do popup mora em
`iris/ui/menu_radial_qt.py`, o app launcher genérico em
`iris/core/app_launcher.py`.

Este é o schema do CORE do IRIS - só guarda dado de "launcher" (favoritos,
categorias, pastas, recentes, apelidos, ícones, uso, limites).
Dado específico de um PLUGIN (ex.: reações da Gala, disparadas pelo plugin
opcional da GAIA) fica em arquivo/namespace separado, nunca aqui - ver
`plugins/iris_plugin_gaia/`.

Esquema (data/menu_radial_config.json):
    {
      "perfil_atual": "Geral",
      "perfis": {
        "Geral": {
          "favoritos": [...nomes de app/itens especiais/categorias, na ordem de exibição...],
          "categorias": {"Nome": {"icone": "📁", "itens": [...nomes...], "ativa": true}},
          "uso": {"nome_do_item": contagem_de_vezes_usado}
        }
      },
      "pastas": {"Nome exibido": {"caminho": "C:/...", "ativa": true}},
      "recentes": [...nomes, mais recente primeiro...],
      "limite_por_camada_favoritos": 8,
      "limite_por_camada_subitens": 8,
      "ranking_automatico_ativo": false,
      "apelidos": {},
      "icones_customizados": {},
      "atalho": "ctrl+alt+space",
      "pasta_projetos": "",          (vazio = pasta que contém este repositório)
      "pasta_icones_projetos": "",
      "projetos_conhecidos": [...nomes já oferecidos à categoria Projects...]
    }

Ver `data/menu_radial_config.example.json` pra um exemplo preenchido (sem
nenhum dado pessoal real - Steam/pastas/uso são só ilustrativos)."""

import os
import re
import copy
import glob
import shutil

from iris.core import armazenamento
from iris.core.atalho import ATALHO_PADRAO
from iris.core.avisos import avisar_usuario, registro

ARQUIVO_DADOS = armazenamento.caminho_dados("menu_radial_config.json")

# Pasta de destino das artes customizadas de ícone - a imagem escolhida na
# tela de Configurações é SEMPRE copiada pra cá, nunca referenciada direto de
# onde o usuário guardou o arquivo original, pra não quebrar se aquela pasta
# for movida/apagada depois.
# No JSON fica o caminho RELATIVO à raiz do projeto (portável entre máquinas);
# `armazenamento.resolver_caminho` devolve o absoluto na hora de abrir.
PASTA_ICONES_CUSTOMIZADOS = "assets/icones_customizados"
EXTENSOES_ICONE_VALIDAS = (".png", ".jpg", ".jpeg", ".ico", ".bmp", ".webp")

# 🔥 Itens ESPECIAIS do CORE (genéricos, sem nenhuma dependência de GAIA) -
# convivem na MESMA lista de favoritos que os nomes de app (são só strings),
# mas em vez de lançar um programa, abrem um SUBMENU radial próprio (mesma
# geometria, itens diferentes, ver iris/ui/menu_radial_qt.py). Categorias
# GAIA-específicas (Funções da Gaia, Avatar/Overlay, Animações do VTube
# Studio, Anime Tracker) NÃO entram aqui - são registradas em runtime pelo
# plugin opcional via `iris.plugins.registry`, o core nunca conhece os nomes
# delas.
ITEM_PASTAS = "📂 Pastas"
ITEM_RECENTES = "🕐 Recentes"
# 🔥 "🎮 Steam" - categoria com TODOS os jogos da Steam instalados agora
# (iris.core.app_launcher.listar_jogos_steam_instalados), sem curadoria
# manual - gerenciada na tela de Configurações, com 1 switch só ligando/
# desligando ela inteira no popup.
ITEM_STEAM = "🎮 Steam"
ITENS_ESPECIAIS = [ITEM_PASTAS, ITEM_RECENTES, ITEM_STEAM]

# Os 4 apps fixos de sempre (iris.core.app_launcher::APPS_FIXOS) - default
# sensato pra quem nunca configurou nada ainda, em vez de um menu radial vazio
# na primeira vez que a tecla de atalho é usada.
FAVORITOS_PADRAO = ["bloco de notas", "calculadora", "youtube", "navegador"]

# Categoria "Projects" - 1 item por projeto do ecossistema, descoberto por
# convenção a cada boot (ver `sincronizar_categoria_projetos`). Nenhum caminho
# de máquina fica no código: a pasta dos projetos vem da configuração
# (`pasta_projetos`; padrão = a pasta que contém este repositório) e a pasta
# de ícones também (`pasta_icones_projetos`, vazia por padrão).
NOME_CATEGORIA_PROJETOS = "Projects"
PREFIXO_PASTA_PROJETO = "project"

PERFIL_PADRAO = "Geral"
LIMITE_POR_CAMADA_PADRAO = 8
MAX_RECENTES = 6

# 🔥 Migração de rótulo (2026-08-30) - categoria de plugin renomeada (`iris_
# plugin_moirai/providers.py::AnimeTrackerProvider.rotulo_categoria`); sem
# isso, o rótulo antigo salvo em `favoritos`/`uso` (posição no círculo,
# contagem de uso acumulada) nunca mais bateria com o provider renomeado -
# a fatia sumiria do popup em silêncio, e o histórico de uso seria perdido.
RENOMEACOES_ROTULO = {"🎬 Anime Tracker": "🎬 Watchlist"}

# Cache validado pelo disco (0.4.0). Histórico: até 2026-09-06 o dict era
# carregado 1x no boot e nunca mais relido - uma edição feita por fora sumia
# na gravação seguinte (mesma classe de bug do Argus/HESTIA/MOIRAI/ECHO, "ler
# 1x, nunca recarregar"). A correção da época foi reler o arquivo em TODA
# chamada, o que custava centenas de leituras por segundo com o popup aberto
# (cada fatia consulta categorias, apelido e ícone a cada repintura). Agora o
# dict fica em memória, mas cada chamada confere data de modificação + tamanho
# do arquivo: mudou por fora, relê. Mantém a garantia e troca o parse por um
# `os.stat`.
_cache_dados = None
_cache_assinatura = None
_lotes_abertos = 0


class leitura_em_lote:
    """`with radial_menu.leitura_em_lote():` confere o disco UMA vez na
    entrada e atende todas as leituras de dentro do bloco direto da memória.
    Pra trechos só de leitura que consultam a configuração dezenas de vezes
    seguidas (uma repintura do popup): no Windows cada `os.stat` custa uma
    fração de milissegundo, e uma repintura fazia mais de dez. Não usar em
    volta de gravações."""

    def __enter__(self):
        global _lotes_abertos
        _carregar()
        _lotes_abertos += 1
        return self

    def __exit__(self, *_exc):
        global _lotes_abertos
        _lotes_abertos -= 1
        return False


def _assinatura_arquivo():
    try:
        st = os.stat(ARQUIVO_DADOS)
        return (ARQUIVO_DADOS, st.st_mtime_ns, st.st_size)
    except OSError:
        return None


def _estrutura_padrao():
    return {
        "perfil_atual": PERFIL_PADRAO,
        "perfis": {
            PERFIL_PADRAO: {
                "favoritos": list(FAVORITOS_PADRAO),
                "categorias": {},
            }
        },
        "pastas": {},
        "recentes": [],
        "limite_por_camada_favoritos": LIMITE_POR_CAMADA_PADRAO,
        "limite_por_camada_subitens": LIMITE_POR_CAMADA_PADRAO,
        "ranking_automatico_ativo": False,
        "apelidos": {},
        "icones_customizados": {},
    }


def _migrar(dados):
    """Aplica as migrações de formato no dict lido. True se algo mudou."""
    mudou = False
    if "limite_por_camada" in dados:
        # o valor único antigo (1 limite pros 2 anéis) vira o ponto de
        # partida dos dois, ajustável separado depois.
        valor_antigo = dados.pop("limite_por_camada")
        dados.setdefault("limite_por_camada_favoritos", valor_antigo)
        dados.setdefault("limite_por_camada_subitens", valor_antigo)
        mudou = True
    pastas_brutas = dados.get("pastas", {})
    if any(not isinstance(v, dict) for v in pastas_brutas.values()):
        # formato antigo era {"Nome": "caminho"}; vira {"Nome": {"caminho":
        # ..., "ativa": true}}.
        dados["pastas"] = {
            nome: (v if isinstance(v, dict) else {"caminho": v, "ativa": True})
            for nome, v in pastas_brutas.items()
        }
        mudou = True
    for perfil in dados.get("perfis", {}).values():
        favoritos = perfil.get("favoritos")
        if favoritos:
            novos = [RENOMEACOES_ROTULO.get(f, f) for f in favoritos]
            if novos != favoritos:
                perfil["favoritos"] = novos
                mudou = True
        uso = perfil.get("uso")
        if uso and any(chave in RENOMEACOES_ROTULO for chave in uso):
            perfil["uso"] = {RENOMEACOES_ROTULO.get(chave, chave): valor for chave, valor in uso.items()}
            mudou = True
    padrao = _estrutura_padrao()
    for chave, valor in padrao.items():
        dados.setdefault(chave, valor)
    if not dados["perfis"]:
        dados["perfis"][PERFIL_PADRAO] = padrao["perfis"][PERFIL_PADRAO]
    if dados["perfil_atual"] not in dados["perfis"]:
        dados["perfil_atual"] = next(iter(dados["perfis"]))
    return mudou


def _ler_do_disco():
    """Lê e migra. Arquivo ilegível NUNCA é sobrescrito pelo padrão: tenta o
    `.bak`; o arquivo ruim é renomeado pra `.corrompido-<data>` e o usuário é
    avisado. Só um arquivo AUSENTE gera a estrutura padrão em silêncio."""
    try:
        dados = armazenamento.ler_json(ARQUIVO_DADOS)
    except armazenamento.ArquivoIlegivel as erro:
        registro.error("Configuração ilegível: %s", erro)
        guardado = armazenamento.separar_arquivo_ilegivel(ARQUIVO_DADOS)
        nome_guardado = os.path.basename(guardado or ARQUIVO_DADOS)
        try:
            dados = armazenamento.ler_json(ARQUIVO_DADOS + ".bak")
        except armazenamento.ArquivoIlegivel:
            dados = None
        if isinstance(dados, dict):
            avisar_usuario(
                "A configuração do menu estava corrompida; restaurei a cópia de segurança. "
                f"O arquivo com problema ficou em {nome_guardado}."
            )
        else:
            dados = _estrutura_padrao()
            avisar_usuario(
                "A configuração do menu estava corrompida e não havia cópia de segurança; "
                f"recomecei do padrão. O arquivo antigo ficou em {nome_guardado}."
            )
        _migrar(dados)
        _salvar(dados)
        return dados
    if not isinstance(dados, dict):
        dados = _estrutura_padrao()
        _salvar(dados)
        return dados
    if _migrar(dados):
        _salvar(dados)  # grava a migração na hora - não só na próxima escrita
    return dados


def _carregar():
    global _cache_dados, _cache_assinatura
    if _lotes_abertos and _cache_dados is not None:
        return _cache_dados
    assinatura = _assinatura_arquivo()
    if _cache_dados is not None and assinatura is not None and assinatura == _cache_assinatura:
        return _cache_dados
    dados = _ler_do_disco()
    _cache_dados = dados
    _cache_assinatura = _assinatura_arquivo()
    return dados


def _salvar(dados):
    global _cache_dados, _cache_assinatura
    armazenamento.gravar_json_atomico(ARQUIVO_DADOS, dados, manter_backup=True)
    _cache_dados = dados
    _cache_assinatura = _assinatura_arquivo()


def esquecer_cache():
    """Força a próxima leitura a vir do disco (testes)."""
    global _cache_dados, _cache_assinatura, _lotes_abertos
    _cache_dados = None
    _cache_assinatura = None
    _lotes_abertos = 0


def _perfil(dados, nome=None):
    nome = nome or dados["perfil_atual"]
    if nome not in dados["perfis"]:
        dados["perfis"][nome] = {"favoritos": [], "categorias": {}, "uso": {}}
    return dados["perfis"][nome]


# ---------- Perfis ----------

def obter_perfil_atual():
    return _carregar()["perfil_atual"]


def obter_nomes_perfis():
    return list(_carregar()["perfis"].keys())


def definir_perfil_atual(nome):
    dados = _carregar()
    if nome in dados["perfis"]:
        dados["perfil_atual"] = nome
        _salvar(dados)


def criar_perfil(nome, copiar_de=None):
    dados = _carregar()
    if not nome or nome in dados["perfis"]:
        return
    if copiar_de and copiar_de in dados["perfis"]:
        dados["perfis"][nome] = copy.deepcopy(dados["perfis"][copiar_de])
    else:
        dados["perfis"][nome] = {"favoritos": [], "categorias": {}}
    _salvar(dados)


def remover_perfil(nome):
    dados = _carregar()
    if len(dados["perfis"]) <= 1 or nome not in dados["perfis"]:
        return  # nunca fica sem nenhum perfil
    del dados["perfis"][nome]
    if dados["perfil_atual"] == nome:
        dados["perfil_atual"] = next(iter(dados["perfis"]))
    _salvar(dados)


def renomear_perfil(nome_antigo, nome_novo):
    dados = _carregar()
    if nome_antigo not in dados["perfis"] or not nome_novo or nome_novo in dados["perfis"]:
        return
    dados["perfis"][nome_novo] = dados["perfis"].pop(nome_antigo)
    if dados["perfil_atual"] == nome_antigo:
        dados["perfil_atual"] = nome_novo
    _salvar(dados)


# ---------- Favoritos ----------

def obter_favoritos(perfil=None):
    """Lista ordenada de nomes (apps/itens especiais/categorias) que aparecem
    no Menu Radial - a ORDEM importa (define a posição no círculo). Devolve
    FAVORITOS_PADRAO se o perfil não tiver nada configurado ainda."""
    dados = _carregar()
    favoritos = _perfil(dados, perfil).get("favoritos", [])
    return favoritos if favoritos else list(FAVORITOS_PADRAO)


def salvar_favoritos(favoritos, perfil=None):
    dados = _carregar()
    _perfil(dados, perfil)["favoritos"] = favoritos
    _salvar(dados)


def obter_favoritos_desativados(perfil=None):
    """Favoritos DESATIVADOS - continuam na lista/posição salva por
    `obter_favoritos`, só somem do popup até reativar."""
    dados = _carregar()
    return set(_perfil(dados, perfil).get("favoritos_desativados", []))


def definir_favorito_ativo(nome, ativo, perfil=None):
    dados = _carregar()
    p = _perfil(dados, perfil)
    desativados = set(p.get("favoritos_desativados", []))
    if ativo:
        desativados.discard(nome)
    else:
        desativados.add(nome)
    p["favoritos_desativados"] = sorted(desativados)
    _salvar(dados)


# ---------- Ranking de frequência de uso ----------

def registrar_uso(rotulo, perfil=None):
    """Conta mais 1 uso pra esse item (app/pasta/categoria) - chamado toda vez
    que ele é realmente ativado no popup (ver iris/ui/menu_radial_qt.py::_lancar).
    Separado de `registrar_recente` de propósito: recentes é sobre ORDEM
    temporal, isso é sobre FREQUÊNCIA acumulada."""
    dados = _carregar()
    uso = _perfil(dados, perfil).setdefault("uso", {})
    uso[rotulo] = uso.get(rotulo, 0) + 1
    _salvar(dados)


def obter_contagem_uso(perfil=None):
    dados = _carregar()
    return dict(_perfil(dados, perfil).get("uso", {}))


def ordenar_favoritos_por_uso(perfil=None):
    """Reordena os favoritos do perfil por frequência de uso (maior primeiro) -
    ordenação ESTÁVEL: itens com a mesma contagem mantêm a ordem relativa
    atual entre si. Chamado sob demanda ou automaticamente ao fechar o popup,
    se `ranking_automatico_ativo` estiver ligado."""
    dados = _carregar()
    p = _perfil(dados, perfil)
    favoritos = p.get("favoritos") or list(FAVORITOS_PADRAO)
    uso = p.get("uso", {})
    favoritos_ordenados = sorted(favoritos, key=lambda r: uso.get(r, 0), reverse=True)
    p["favoritos"] = favoritos_ordenados
    _salvar(dados)
    return favoritos_ordenados


def obter_ranking_automatico_ativo():
    return _carregar().get("ranking_automatico_ativo", False)


def salvar_ranking_automatico_ativo(ativo):
    dados = _carregar()
    dados["ranking_automatico_ativo"] = bool(ativo)
    _salvar(dados)


# ---------- Categorias (submenus criados pelo usuário) ----------

def obter_categorias(perfil=None):
    """{"Nome da categoria": {"icone": "📁", "itens": [...nomes de app...], "ativa": bool}}"""
    dados = _carregar()
    return _perfil(dados, perfil).get("categorias", {})


def salvar_categoria(nome_categoria, itens, icone="📁", perfil=None, itens_desativados=None):
    """Cria OU edita (mesmo nome = sobrescreve os itens/ícone). Preserva o
    estado `ativa` de uma categoria já existente. `itens_desativados` (None
    preserva o que já estava salvo) sempre filtrado pra só conter nomes que
    ainda estão em `itens`."""
    dados = _carregar()
    categorias = _perfil(dados, perfil).setdefault("categorias", {})
    existente = categorias.get(nome_categoria, {})
    ativa_atual = existente.get("ativa", True)
    desativados_base = itens_desativados if itens_desativados is not None else existente.get("itens_desativados", [])
    desativados_validos = [d for d in desativados_base if d in itens]
    categorias[nome_categoria] = {"icone": icone, "itens": list(itens), "ativa": ativa_atual, "itens_desativados": desativados_validos}
    _salvar(dados)


def obter_categoria_itens_desativados(nome_categoria, perfil=None):
    dados = _carregar()
    categoria = _perfil(dados, perfil).get("categorias", {}).get(nome_categoria, {})
    return set(categoria.get("itens_desativados", []))


def definir_categoria_item_ativo(nome_categoria, item, ativo, perfil=None):
    """Liga/desliga um ITEM específico dentro de uma categoria, sem removê-lo
    da lista."""
    dados = _carregar()
    categoria = _perfil(dados, perfil).get("categorias", {}).get(nome_categoria)
    if not categoria:
        return
    desativados = set(categoria.get("itens_desativados", []))
    if ativo:
        desativados.discard(item)
    else:
        desativados.add(item)
    categoria["itens_desativados"] = sorted(desativados)
    _salvar(dados)


def definir_categoria_ativa(nome_categoria, ativa, perfil=None):
    """Liga/desliga uma categoria sem apagar ela - desativada some do popup
    radial na hora, mas mantém a posição exata dela nos favoritos."""
    dados = _carregar()
    categorias = _perfil(dados, perfil).get("categorias", {})
    if nome_categoria in categorias:
        categorias[nome_categoria]["ativa"] = bool(ativa)
        _salvar(dados)


def remover_categoria(nome_categoria, perfil=None):
    dados = _carregar()
    _perfil(dados, perfil).get("categorias", {}).pop(nome_categoria, None)
    _salvar(dados)


# ---------- Apelidos: renomear a EXIBIÇÃO sem mexer na identidade real do
# item ----------
# GLOBAL (não por perfil, de propósito) - "calculadora" continua sendo
# "calculadora" pra achar/abrir o app de verdade (find_app) ou bater com a
# sentinela de um item especial; o apelido troca só o TEXTO exibido em
# QUALQUER anel (ver iris/ui/menu_radial_qt.py::RadialMenuQt._resolver_item).

def obter_apelido(item_real):
    return _carregar().get("apelidos", {}).get(item_real)


def definir_apelido(item_real, apelido):
    dados = _carregar()
    dados.setdefault("apelidos", {})[item_real] = apelido
    _salvar(dados)


def remover_apelido(item_real):
    dados = _carregar()
    dados.get("apelidos", {}).pop(item_real, None)
    _salvar(dados)


# ---------- Ícones customizados: trocar o ÍCONE sem mexer na identidade real
# do item ----------
# GLOBAL, mesmo padrão dos apelidos - sobrepõe o ícone padrão resolvido (fixo,
# real da Steam, ou de uma categoria) mas nunca muda a identidade usada pra
# achar/abrir o item. Guarda ou um emoji/texto de exibição (comportamento
# original) ou o caminho de uma imagem própria copiada pra dentro do projeto -
# `eh_caminho_icone_customizado` distingue os dois casos só pela extensão.

def obter_icone_customizado(item_real):
    return _carregar().get("icones_customizados", {}).get(item_real)


def definir_icone_customizado(item_real, icone):
    dados = _carregar()
    dados.setdefault("icones_customizados", {})[item_real] = icone
    _salvar(dados)


def remover_icone_customizado(item_real):
    dados = _carregar()
    dados.get("icones_customizados", {}).pop(item_real, None)
    _salvar(dados)


def eh_caminho_icone_customizado(valor):
    """True se o ícone customizado guardado for o caminho de uma imagem (em vez
    de emoji/texto) - basta olhar a extensão, sem precisar tocar o disco."""
    if not valor:
        return False
    _, ext = os.path.splitext(valor)
    return ext.lower() in EXTENSOES_ICONE_VALIDAS


def definir_icone_customizado_arquivo(item_real, caminho_origem):
    """Copia a imagem escolhida na tela de Configurações pra
    `PASTA_ICONES_CUSTOMIZADOS` (dentro do projeto) e salva o caminho relativo
    como ícone customizado do item. Copiar em vez de referenciar o arquivo
    original evita que o menu perca o ícone se o usuário mover/apagar a pasta
    de onde a imagem veio. Retorna o caminho relativo salvo."""
    os.makedirs(armazenamento.resolver_caminho(PASTA_ICONES_CUSTOMIZADOS), exist_ok=True)
    _, ext = os.path.splitext(caminho_origem)
    nome_arquivo = re.sub(r"[^a-z0-9]+", "_", item_real.strip().lower()).strip("_") + ext.lower()
    caminho_destino = f"{PASTA_ICONES_CUSTOMIZADOS}/{nome_arquivo}"
    destino_absoluto = armazenamento.resolver_caminho(caminho_destino)
    if os.path.abspath(caminho_origem) != os.path.abspath(destino_absoluto):
        shutil.copyfile(caminho_origem, destino_absoluto)
    definir_icone_customizado(item_real, caminho_destino)
    return caminho_destino


def obter_personalizacoes():
    """{item_real: {"apelido": ..., "icone": ...}} de tudo que tem apelido
    e/ou ícone customizado - pra tela de Configurações listar."""
    dados = _carregar()
    resultado = {}
    for item, apelido in dados.get("apelidos", {}).items():
        resultado.setdefault(item, {})["apelido"] = apelido
    for item, icone in dados.get("icones_customizados", {}).items():
        resultado.setdefault(item, {})["icone"] = icone
    return resultado


# ---------- Steam: ordem manual + toggle por jogo ----------
# Guardado por PERFIL, igual favoritos/categorias. A lista de jogos instalados
# de verdade é sempre a fonte de verdade (app_launcher.
# listar_jogos_steam_instalados) - aqui só guardamos ORDEM (quem já foi visto,
# em que posição) e quais estão DESATIVADOS.

def obter_steam_ordem(perfil=None):
    dados = _carregar()
    return list(_perfil(dados, perfil).get("steam_ordem", []))


def salvar_steam_ordem(ordem, perfil=None):
    dados = _carregar()
    _perfil(dados, perfil)["steam_ordem"] = list(ordem)
    _salvar(dados)


def obter_steam_desativados(perfil=None):
    dados = _carregar()
    return set(_perfil(dados, perfil).get("steam_desativados", []))


def definir_steam_jogo_ativo(nome_jogo, ativo, perfil=None):
    dados = _carregar()
    p = _perfil(dados, perfil)
    desativados = set(p.get("steam_desativados", []))
    if ativo:
        desativados.discard(nome_jogo)
    else:
        desativados.add(nome_jogo)
    p["steam_desativados"] = sorted(desativados)
    _salvar(dados)


def mesclar_ordem_steam(jogos_instalados, perfil=None):
    """Combina a ordem já salva com o que está instalado AGORA
    (`jogos_instalados`, passado por quem chama - normalmente
    `app_launcher.listar_jogos_steam_instalados()`, pra este módulo continuar
    sem nenhuma dependência de UI): jogo desinstalado some sozinho mesmo que
    ainda esteja na ordem salva; jogo NOVO entra sozinho no FIM."""
    ordem_salva = obter_steam_ordem(perfil)
    instalados = set(jogos_instalados)
    ordem_valida = [j for j in ordem_salva if j in instalados]
    novos = [j for j in jogos_instalados if j not in ordem_salva]
    return ordem_valida + novos


# ---------- Pastas (atalhos que abrem no Explorer) ----------
# Formato interno: {"Nome": {"caminho": "C:/...", "ativa": bool}} - migrado
# automaticamente do formato antigo ({"Nome": "caminho"}, plano) na primeira
# carga, ver _carregar().

def obter_pastas():
    """{"Nome": "caminho"} - só as pastas ATIVAS."""
    dados = _carregar()
    return {nome: info["caminho"] for nome, info in dados.get("pastas", {}).items() if info.get("ativa", True)}


def obter_pastas_todas():
    """{"Nome": {"caminho":..., "ativa":...}} - TODAS as pastas (ativas e
    desativadas), pra tela de Configurações gerenciar."""
    return dict(_carregar().get("pastas", {}))


def adicionar_pasta(nome_exibido, caminho):
    dados = _carregar()
    pastas = dados.setdefault("pastas", {})
    ativa_atual = pastas.get(nome_exibido, {}).get("ativa", True)
    pastas[nome_exibido] = {"caminho": caminho, "ativa": ativa_atual}
    _salvar(dados)


# ---------- Categoria "Projects": descoberta automática ----------

def obter_pasta_projetos():
    """Pasta onde ficam os projetos do ecossistema. Sem nada configurado, é a
    pasta que contém este repositório (os projetos irmãos ficam lado a lado)."""
    return _carregar().get("pasta_projetos") or os.path.dirname(armazenamento.RAIZ_PROJETO)


def salvar_pasta_projetos(caminho):
    dados = _carregar()
    dados["pasta_projetos"] = (caminho or "").strip()
    _salvar(dados)


def obter_pasta_icones_projetos():
    return _carregar().get("pasta_icones_projetos", "")


def salvar_pasta_icones_projetos(caminho):
    dados = _carregar()
    dados["pasta_icones_projetos"] = (caminho or "").strip()
    _salvar(dados)


def _nome_projeto(nome_pasta):
    """"Project-ARGUS" -> "ARGUS"; "Project G.A.I.A" -> "GAIA". None se a
    pasta não segue a convenção."""
    if not nome_pasta.lower().startswith(PREFIXO_PASTA_PROJETO):
        return None
    resto = nome_pasta[len(PREFIXO_PASTA_PROJETO):]
    if not resto or resto[0] not in "-_ ":
        return None
    nome = re.sub(r"[^A-Za-z0-9]+", "", resto).upper()
    return nome or None


def _achar_inicializador(pasta_projeto, nome):
    """O inicializador escondido (`iniciar_*_oculto.vbs`) na raiz do projeto
    ou 1 nível abaixo (a GAIA guarda o dela em `assistant/`); na falta dele,
    `iniciar_*.bat` ou `<NOME>.bat` na raiz. None se não houver nenhum."""
    for padrao in (
        os.path.join(pasta_projeto, "iniciar_*_oculto.vbs"),
        os.path.join(pasta_projeto, "*", "iniciar_*_oculto.vbs"),
    ):
        achados = sorted(glob.glob(padrao))
        if achados:
            return achados[0]
    candidatos = sorted(
        c for c in glob.glob(os.path.join(pasta_projeto, "iniciar_*.bat"))
        if "debug" not in os.path.basename(c).lower()
    )
    if candidatos:
        return candidatos[0]
    direto = os.path.join(pasta_projeto, f"{nome}.bat")
    return direto if os.path.isfile(direto) else None


def _achar_icone_projeto(pasta_icones, nome):
    if not pasta_icones or not os.path.isdir(pasta_icones):
        return None
    try:
        arquivos = os.listdir(pasta_icones)
    except OSError:
        return None
    for arquivo in arquivos:
        base, ext = os.path.splitext(arquivo)
        if base.lower() == nome.lower() and ext.lower() in EXTENSOES_ICONE_VALIDAS:
            return os.path.join(pasta_icones, arquivo)
    return None


def descobrir_projetos(pasta_projetos=None, pasta_icones=None):
    """Lista de {"nome", "pasta", "inicializador", "icone"} pra cada pasta
    `Project*` encontrada. O próprio IRIS nunca ganha inicializador (a
    instância que mostra o popup já É o IRIS rodando; abrir de novo só
    bateria na trava de instância única) - o item dele abre a pasta."""
    pasta_projetos = pasta_projetos or obter_pasta_projetos()
    pasta_icones = obter_pasta_icones_projetos() if pasta_icones is None else pasta_icones
    projetos = []
    try:
        entradas = sorted(os.listdir(pasta_projetos), key=str.lower)
    except OSError:
        return projetos
    for entrada in entradas:
        caminho = os.path.join(pasta_projetos, entrada)
        nome = _nome_projeto(entrada)
        if not nome or not os.path.isdir(caminho):
            continue
        proprio_iris = os.path.normcase(os.path.abspath(caminho)) == os.path.normcase(armazenamento.RAIZ_PROJETO)
        projetos.append({
            "nome": nome,
            "pasta": caminho,
            "inicializador": None if proprio_iris else _achar_inicializador(caminho, nome),
            "icone": _achar_icone_projeto(pasta_icones, nome),
        })
    return projetos


def sincronizar_categoria_projetos():
    """Chamado no boot (`iris/main.py`) e pelo botão em Configurações.
    Acrescenta à categoria "Projects" só os projetos que o IRIS ainda não
    conhecia (`projetos_conhecidos`): um projeto novo no disco aparece
    sozinho, e um item que o usuário removeu da categoria não volta. Se o
    usuário apagou a categoria inteira, ela também não é recriada. Devolve os
    nomes adicionados."""
    dados = _carregar()
    categorias = _perfil(dados).setdefault("categorias", {})
    categoria = categorias.get(NOME_CATEGORIA_PROJETOS)
    conhecidos = dados.get("projetos_conhecidos")
    primeira_vez = conhecidos is None and not dados.get("categoria_projetos_criada_v2")
    if conhecidos is None:
        # Vindo do seed antigo (até a 0.3.0): tudo que já está na categoria
        # conta como conhecido, com ou sem o prefixo de pasta.
        conhecidos = [re.sub(r"[^A-Za-z0-9]+", "", i).upper() for i in (categoria or {}).get("itens", [])]
    conhecidos = set(conhecidos)

    projetos = descobrir_projetos()
    novos = [p for p in projetos if p["nome"] not in conhecidos]
    adicionados = []
    if novos and (categoria is not None or primeira_vez):
        from iris.core import app_launcher

        itens = list((categoria or {}).get("itens", []))
        for projeto in novos:
            nome = projeto["nome"]
            if projeto["inicializador"]:
                app_launcher.adicionar_app_manual(nome, projeto["inicializador"])
                rotulo = nome
            else:
                if nome not in obter_pastas_todas():
                    adicionar_pasta(nome, projeto["pasta"])
                rotulo = f"📁 {nome}"
            if rotulo not in itens:
                itens.append(rotulo)
                adicionados.append(nome)
            if projeto["icone"] and not obter_icone_customizado(rotulo):
                try:
                    definir_icone_customizado_arquivo(rotulo, projeto["icone"])
                except OSError as erro:
                    registro.warning("Ícone de %s não copiado: %s", nome, erro)
        salvar_categoria(NOME_CATEGORIA_PROJETOS, itens, icone=(categoria or {}).get("icone", "📁"))
        if primeira_vez:
            favoritos = obter_favoritos()
            if NOME_CATEGORIA_PROJETOS not in favoritos:
                salvar_favoritos(favoritos + [NOME_CATEGORIA_PROJETOS])

    dados = _carregar()
    dados["projetos_conhecidos"] = sorted(conhecidos | {p["nome"] for p in projetos})
    dados["categoria_projetos_criada_v2"] = True
    _salvar(dados)
    return adicionados


# ---------- Atalho global ----------

def obter_atalho():
    return _carregar().get("atalho") or ATALHO_PADRAO


def salvar_atalho(atalho_canonico):
    dados = _carregar()
    dados["atalho"] = atalho_canonico
    _salvar(dados)


def importar_pastas(pastas_novas):
    """Mescla pastas vindas de outro `menu_radial_config.json` compatível
    (mesmo schema - ex.: o Menu Radial da GAIA) - sobrescreve por nome,
    preserva as pastas já existentes que não estão em `pastas_novas`."""
    dados = _carregar()
    pastas = dados.setdefault("pastas", {})
    importadas = 0
    for nome, info in (pastas_novas or {}).items():
        caminho = info.get("caminho") if isinstance(info, dict) else None
        if not caminho:
            continue
        pastas[nome] = {"caminho": caminho, "ativa": bool(info.get("ativa", True))}
        importadas += 1
    _salvar(dados)
    return importadas


def renomear_pasta(nome_antigo, nome_novo, caminho_novo):
    """Edita uma pasta já cadastrada - troca nome e/ou caminho preservando o
    estado ativa/desativada."""
    dados = _carregar()
    pastas = dados.setdefault("pastas", {})
    if nome_antigo not in pastas:
        return
    info = pastas.pop(nome_antigo)
    info["caminho"] = caminho_novo
    pastas[nome_novo] = info
    _salvar(dados)


def remover_pasta(nome_exibido):
    dados = _carregar()
    dados.get("pastas", {}).pop(nome_exibido, None)
    _salvar(dados)


def definir_pasta_ativa(nome_exibido, ativa):
    dados = _carregar()
    pastas = dados.get("pastas", {})
    if nome_exibido in pastas:
        pastas[nome_exibido]["ativa"] = bool(ativa)
        _salvar(dados)


# ---------- Recentes ----------

def obter_recentes():
    return list(_carregar().get("recentes", []))


def registrar_recente(nome_item):
    """Chamado toda vez que um item do menu é ativado - mantém os MAX_RECENTES
    mais recentes, sem duplicar (usar de novo manda o item pro topo da lista)."""
    dados = _carregar()
    recentes = [r for r in dados.get("recentes", []) if r != nome_item]
    recentes.insert(0, nome_item)
    dados["recentes"] = recentes[:MAX_RECENTES]
    _salvar(dados)


# ---------- Limite de itens por camada (separado por anel - o interno,
# sempre visível, pode ter um limite diferente do anel de subitens de uma
# categoria) ----------

def obter_limite_por_camada_favoritos():
    return _carregar().get("limite_por_camada_favoritos", LIMITE_POR_CAMADA_PADRAO)


def salvar_limite_por_camada_favoritos(limite):
    dados = _carregar()
    dados["limite_por_camada_favoritos"] = max(3, int(limite))
    _salvar(dados)


def obter_limite_por_camada_subitens():
    return _carregar().get("limite_por_camada_subitens", LIMITE_POR_CAMADA_PADRAO)


def salvar_limite_por_camada_subitens(limite):
    dados = _carregar()
    dados["limite_por_camada_subitens"] = max(3, int(limite))
    _salvar(dados)

