# -*- coding: utf-8 -*-
"""Registro em memória dos `ActionProvider` conhecidos pelo processo atual -
populado por quem sobe o app (`iris/main.py`, tentando importar pacotes de
plugin opcionais instalados) ANTES do popup abrir pela 1a vez. O popup
(`iris/ui/menu_radial_qt.py`) só consulta `providers_disponiveis()`, nunca
conhece nenhum plugin especifico em tempo de import."""

from concurrent.futures import ThreadPoolExecutor

from iris.plugins.base import CAPACIDADES_CONHECIDAS

_providers = []
_ultimos_disponiveis = []


def registrar_provider(provider):
    """Idempotente por `id` - registrar de novo o mesmo id SUBSTITUI a
    instância antiga (útil se `main.py` recarregar plugins), nunca duplica a
    categoria no popup."""
    capacidades = set(provider.capacidades())
    desconhecidas = capacidades - CAPACIDADES_CONHECIDAS
    if desconhecidas:
        raise ValueError(
            f"Provider '{provider.id}' declarou capacidades desconhecidas: "
            f"{', '.join(sorted(desconhecidas))}"
        )
    if float(provider.tempo_limite_segundos) <= 0:
        raise ValueError(f"Provider '{provider.id}' precisa declarar timeout positivo.")
    global _providers
    _providers = [p for p in _providers if p.id != provider.id] + [provider]


def remover_provider(id_provider):
    global _providers
    _providers = [p for p in _providers if p.id != id_provider]


def providers_registrados():
    """TODOS os providers registrados, disponíveis ou não - útil pra UI de
    diagnóstico/Configurações mostrar o que está instalado."""
    return list(_providers)


def _responde(provider):
    try:
        return bool(provider.esta_disponivel())
    except Exception:
        return False


def providers_disponiveis():
    """Só os providers que responderam `esta_disponivel() == True` AGORA.
    As checagens rodam em PARALELO: cada uma pode esperar o timeout de uma
    porta fechada, e em série o atraso somava (4 serviços parados = 4
    timeouts). Bloqueia até a mais lenta terminar - na thread da interface,
    preferir `disponiveis_em_cache()` + `atualizar_disponibilidade()` numa
    thread. O resultado também alimenta o cache."""
    global _ultimos_disponiveis
    providers = list(_providers)
    if not providers:
        _ultimos_disponiveis = []
        return []
    with ThreadPoolExecutor(max_workers=len(providers)) as executor:
        respostas = list(executor.map(_responde, providers))
    disponiveis = [p for p, ok in zip(providers, respostas) if ok]
    _ultimos_disponiveis = [p.id for p in disponiveis]
    return disponiveis


atualizar_disponibilidade = providers_disponiveis


def disponiveis_em_cache():
    """Resultado da ÚLTIMA checagem, sem tocar a rede - o popup abre na hora
    com isto e se corrige quando a checagem em segundo plano termina. Vazio
    antes da primeira checagem."""
    ids = set(_ultimos_disponiveis)
    return [p for p in _providers if p.id in ids]


def provider_por_categoria(rotulo_categoria):
    for provider in _providers:
        if provider.rotulo_categoria == rotulo_categoria:
            return provider
    return None


def executar_provider(provider, item, confirmar=None):
    """Aplica o portão de confirmação e executa uma ação do provider.

    ``confirmar`` recebe a mensagem declarada pelo plugin. A ausência de um
    callback bloqueia uma ação sensível, o que mantém consumidores futuros em
    fail-closed.
    """
    mensagem = provider.confirmacao_para(item)
    if mensagem and (confirmar is None or not confirmar(mensagem)):
        return False
    provider.executar(item)
    return True
