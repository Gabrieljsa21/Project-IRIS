# -*- coding: utf-8 -*-
"""`AnimeTrackerProvider` - extraído de `iris_plugin_gaia/providers.py`
(2026-08-24) quando o Assistente de Animes deixou de ser hospedado pela GAIA
e ganhou processo próprio (Project-MOIRAI, porta 8768). Mesmo contrato HTTP
de sempre (`/anime/tenho_interesse`, `/anime/adicionar`, `/anime/assistir/
<titulo>`) - só a URL base mudou, de `iris_plugin_gaia.providers.
URL_BASE_BRIDGE` (GAIA, porta 8766) pra aqui (MOIRAI, porta 8768)."""

import json
import os
import socket
import threading
import urllib.parse
import urllib.request

from PySide6.QtGui import QGuiApplication

from iris.plugins.base import ActionProvider

URL_BASE_MOIRAI = os.environ.get("IRIS_MOIRAI_URL", "http://127.0.0.1:8768")

_ITEM_ACAO_ADICIONAR_ANIME = "➕ Adicionar Anime"


def _porta_responde(url_base, timeout=0.3):
    """Checagem de disponibilidade não-invasiva - só confere se algo está
    escutando na porta (TCP connect), sem chamar nenhuma rota de verdade."""
    try:
        host_porta = url_base.split("://", 1)[-1]
        host, _, porta = host_porta.partition(":")
        with socket.create_connection((host, int(porta or 80)), timeout=timeout):
            return True
    except OSError:
        return False


class AnimeTrackerProvider(ActionProvider):
    """FUNCIONAL - fala direto com o Project-MOIRAI (processo próprio, dono
    do estado dos animes desde 2026-08-24)."""

    id = "moirai_anime_tracker"
    rotulo_categoria = "🎬 Anime Tracker"

    def esta_disponivel(self):
        return _porta_responde(URL_BASE_MOIRAI)

    def listar_subitens(self):
        try:
            with urllib.request.urlopen(URL_BASE_MOIRAI + "/anime/tenho_interesse", timeout=2) as resp:
                titulos = json.loads(resp.read())
        except Exception:
            titulos = []
        itens = [_ITEM_ACAO_ADICIONAR_ANIME]
        itens += [f"🎬 {t}" for t in titulos] if titulos else ["ℹ️ Nenhum anime rastreado ainda"]
        return itens

    def executar(self, item):
        if item == _ITEM_ACAO_ADICIONAR_ANIME:
            link = QGuiApplication.clipboard().text().strip()
            if not link.lower().startswith(("http://", "https://")):
                print(" [SISTEMA] IRIS (plugin MOIRAI): copie o link da página do anime antes de usar 'Adicionar Anime'.")
                return

            def _adicionar():
                try:
                    corpo = json.dumps({"url": link}).encode("utf-8")
                    req = urllib.request.Request(
                        URL_BASE_MOIRAI + "/anime/adicionar", data=corpo, method="POST",
                        headers={"Content-Type": "application/json"},
                    )
                    # 🔥 Síncrono do lado do MOIRAI (scraping de verdade), por
                    # isso um timeout bem maior que o padrão de 2s.
                    with urllib.request.urlopen(req, timeout=30) as resp:
                        resultado = json.loads(resp.read())
                    chave = resultado.get("chave")
                    if not resultado.get("erro") and chave:
                        # 🔥 2 chamadas de propósito (2026-08-24) - o IRIS não
                        # tem seletor de episódios (isso só existe na UI rica
                        # do Painel da GAIA), então baixa tudo que estiver
                        # pendente igual sempre fez, só que agora como um
                        # passo separado (`/anime/adicionar` não baixa mais
                        # sozinho, ver `moirai/api_bridge.py`).
                        urllib.request.urlopen(urllib.request.Request(
                            URL_BASE_MOIRAI + "/anime/baixar_pendentes",
                            data=json.dumps({"chave": chave}).encode("utf-8"), method="POST",
                            headers={"Content-Type": "application/json"},
                        ), timeout=30)
                except Exception:
                    print(" [SISTEMA] IRIS (plugin MOIRAI): não consegui adicionar o anime - confira se o MOIRAI está rodando.")
            threading.Thread(target=_adicionar, daemon=True).start()
            return

        titulo = item[len("🎬 "):] if item.startswith("🎬 ") else item

        def _assistir():
            try:
                rota = "/anime/assistir/" + urllib.parse.quote(titulo, safe="")
                urllib.request.urlopen(urllib.request.Request(URL_BASE_MOIRAI + rota, method="POST"), timeout=2)
            except Exception:
                print(" [SISTEMA] IRIS (plugin MOIRAI): não consegui abrir o episódio - confira se o MOIRAI está rodando.")
        threading.Thread(target=_assistir, daemon=True).start()
