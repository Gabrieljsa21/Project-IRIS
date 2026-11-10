"""Isola cada teste dos dados reais: os módulos de persistência passam a
gravar numa pasta temporária, nunca em `data/` do repositório."""
import os
import sys

import pytest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
sys.path.insert(0, os.path.join(RAIZ, "plugins", "iris_plugin_moirai"))


@pytest.fixture
def dados_isolados(tmp_path, monkeypatch):
    from iris.core import app_launcher, apps_scanner, avisos, radial_menu

    monkeypatch.setattr(radial_menu, "ARQUIVO_DADOS", str(tmp_path / "menu_radial_config.json"))
    monkeypatch.setattr(app_launcher, "ARQUIVO_APPS_MANUAIS", str(tmp_path / "apps_manuais.json"))
    monkeypatch.setattr(apps_scanner, "ARQUIVO_ESCANEADOS", str(tmp_path / "apps_escaneados.json"))
    radial_menu.esquecer_cache()
    recebidos = []
    monkeypatch.setattr(avisos, "_notificador", recebidos.append)
    yield tmp_path, recebidos
    radial_menu.esquecer_cache()
