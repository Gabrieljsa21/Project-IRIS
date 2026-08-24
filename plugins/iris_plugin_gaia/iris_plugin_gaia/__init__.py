# -*- coding: utf-8 -*-
"""Plugin opcional que conecta o IRIS à GAIA (`Project G.A.I.A/assistant`,
processo separado) - implementa os 3 pontos de acoplamento que ainda são da
GAIA (ver `ARQUITETURA.md` do repo `Project-IRIS` e o `TODO.md` deste
pacote; o 4º ponto, Anime Tracker, mudou pra `iris_plugin_moirai` em
2026-08-24). Só quem tem a GAIA rodando instala isto (`pip install -e
plugins/iris_plugin_gaia`, com `iris` já instalado no mesmo venv) - o core
do IRIS nunca importa nada daqui."""

from iris.plugins.registry import registrar_provider

from iris_plugin_gaia.providers import (
    AnimacoesVTSProvider,
    AvatarOverlayProvider,
    FuncoesGaiaProvider,
)


def registrar():
    """Chamado por `iris/main.py` no boot (via `importlib.import_module` +
    `getattr(modulo, "registrar")`) - registra os 3 providers no registry
    global do IRIS. Cada um decide sozinho, via `esta_disponivel()`, se
    aparece de verdade no popup agora."""
    registrar_provider(AvatarOverlayProvider())
    registrar_provider(AnimacoesVTSProvider())
    registrar_provider(FuncoesGaiaProvider())
