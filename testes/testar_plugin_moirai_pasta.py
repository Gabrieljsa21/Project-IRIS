"""Teste isolado do item de pasta do plugin MOIRAI."""
import json
import os
import sys
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "plugins", "iris_plugin_moirai"))

from iris_plugin_moirai import providers


class _Resposta:
    def __init__(self, dados):
        self._dados = json.dumps(dados).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self._dados


def testar_item_existe_sem_anime_pronto():
    with mock.patch.object(providers.urllib.request, "urlopen", return_value=_Resposta([])):
        itens = providers.AnimeTrackerProvider().listar_subitens()
    assert providers._ITEM_ACAO_ADICIONAR_ANIME in itens
    assert providers._ITEM_ABRIR_PASTA_DOWNLOADS in itens
    assert any("Nenhum anime" in item for item in itens)


if __name__ == "__main__":
    testar_item_existe_sem_anime_pronto()
    print("PASS: item da pasta de downloads no plugin MOIRAI")
