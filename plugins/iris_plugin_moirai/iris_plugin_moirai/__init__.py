# -*- coding: utf-8 -*-
"""Plugin opcional que conecta o IRIS ao Project-MOIRAI (animes/episódios,
processo separado) - extraído de dentro do `iris_plugin_gaia` em 2026-08-24,
quando o Assistente de Animes deixou de ser hospedado pela GAIA (ver
`Project G.A.I.A/assistant/docs/TODO.md` -> "Arquitetura do ecossistema").
Só quem tem o MOIRAI rodando instala isto (`pip install -e plugins/
iris_plugin_moirai`, com `iris` já instalado no mesmo venv) - o core do
IRIS nunca importa nada daqui."""

from iris.plugins.registry import registrar_provider

from iris_plugin_moirai.providers import AnimeTrackerProvider


def registrar():
    """Chamado por `iris/main.py` no boot (via `importlib.import_module` +
    `getattr(modulo, "registrar")`)."""
    registrar_provider(AnimeTrackerProvider())
