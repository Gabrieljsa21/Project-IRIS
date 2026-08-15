# -*- coding: utf-8 -*-
"""Registro em memória dos `ActionProvider` conhecidos pelo processo atual -
populado por quem sobe o app (`iris/main.py`, tentando importar pacotes de
plugin opcionais instalados) ANTES do popup abrir pela 1a vez. O popup
(`iris/ui/menu_radial_qt.py`) só consulta `providers_disponiveis()`, nunca
conhece nenhum plugin especifico em tempo de import."""

_providers = []


def registrar_provider(provider):
    """Idempotente por `id` - registrar de novo o mesmo id SUBSTITUI a
    instância antiga (útil se `main.py` recarregar plugins), nunca duplica a
    categoria no popup."""
    global _providers
    _providers = [p for p in _providers if p.id != provider.id] + [provider]


def remover_provider(id_provider):
    global _providers
    _providers = [p for p in _providers if p.id != id_provider]


def providers_registrados():
    """TODOS os providers registrados, disponíveis ou não - útil pra UI de
    diagnóstico/Configurações mostrar o que está instalado."""
    return list(_providers)


def providers_disponiveis():
    """Só os providers que responderam `esta_disponivel() == True` AGORA -
    consultado pelo popup toda vez que abre (nunca cacheado aqui, o estado de
    disponibilidade pode mudar a qualquer momento, ex.: GAIA foi fechada)."""
    disponiveis = []
    for provider in _providers:
        try:
            if provider.esta_disponivel():
                disponiveis.append(provider)
        except Exception:
            continue
    return disponiveis


def provider_por_categoria(rotulo_categoria):
    for provider in _providers:
        if provider.rotulo_categoria == rotulo_categoria:
            return provider
    return None
