# -*- coding: utf-8 -*-
"""Os 3 `ActionProvider` que conectam o IRIS à GAIA - todos funcionais hoje,
ver `TODO.md` deste pacote pro detalhe de cada um. O 4º (`AnimeTrackerProvider`)
mudou pra `iris_plugin_moirai` em 2026-08-24 (ver esse pacote/ARQUITETURA.md)."""

import json
import os
import socket
import threading
import urllib.parse
import urllib.request

from iris.plugins.base import ActionProvider

# Base da API HTTP local do overlay (`vtuber_overlay.py`, porta 8765 - já
# existente na GAIA, sem nenhuma mudança necessária do lado dela).
# Sobrescrevível via variável de ambiente pra quem roda a GAIA numa porta
# diferente.
URL_BASE_OVERLAY = os.environ.get("IRIS_GAIA_OVERLAY_URL", "http://127.0.0.1:8765")

# Servidor novo (2026-08-21) pra "Funções da Gaia" - roda no PROCESSO
# PRINCIPAL da GAIA (`integrations/iris_bridge.py`), sempre ativo, diferente
# do 8765 acima (que só sobe se o Avatar Virtual estiver ligado). Ver
# `TODO.md` deste pacote.
URL_BASE_BRIDGE = os.environ.get("IRIS_GAIA_BRIDGE_URL", "http://127.0.0.1:8766")

# Mesmo mapa rótulo -> rota de `Project G.A.I.A/assistant/ui/menu_radial_qt.py`
# (`_ROTULO_PARA_ROTA_OVERLAY`) - as rotas em si não mudam entre GAIA e IRIS,
# só quem as chama.
ROTULO_PARA_ROTA_OVERLAY = {
    "🔒 Travar/Destravar": "/lock/toggle",
    "👆 Click-through": "/click/toggle",
    "⬆️ Mover Cima": "/move/up",
    "⬇️ Mover Baixo": "/move/down",
    "⬅️ Mover Esquerda": "/move/left",
    "➡️ Mover Direita": "/move/right",
    "➕ Aumentar": "/resize/up",
    "➖ Diminuir": "/resize/down",
    "🔄 Reencontrar VTS": "/find",
    "💾 Salvar Posição Atual": "/position/save",
    "❌ Fechar Overlay": "/close",
}


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


class AvatarOverlayProvider(ActionProvider):
    """FUNCIONAL - reaproveita a API HTTP já existente do overlay (porta
    8765), sem nenhuma mudança do lado da GAIA. Ponto de acoplamento #2 da
    extração original (`_chamar_overlay`, `Project G.A.I.A/assistant/ui/
    menu_radial_qt.py`)."""

    id = "gaia_avatar_overlay"
    rotulo_categoria = "🖥️ Avatar (Overlay)"

    def esta_disponivel(self):
        return _porta_responde(URL_BASE_OVERLAY)

    def listar_subitens(self):
        return list(ROTULO_PARA_ROTA_OVERLAY.keys())

    def executar(self, item):
        rota = ROTULO_PARA_ROTA_OVERLAY.get(item)
        if not rota:
            return

        def _chamar():
            try:
                urllib.request.urlopen(urllib.request.Request(URL_BASE_OVERLAY + rota, method="POST"), timeout=2)
            except Exception:
                print(" [SISTEMA] IRIS (plugin GAIA): Avatar Overlay não respondeu - confira se a GAIA está rodando com o overlay ligado.")
        threading.Thread(target=_chamar, daemon=True).start()


class AnimacoesVTSProvider(ActionProvider):
    """FUNCIONAL (2026-08-21) - a GAIA fala com o VTube Studio via
    `integrations.vtubestudio.vtube_studio_client.VTubeStudioClient`
    (websocket direto, processo da GAIA), então este provider passa pelos 2
    endpoints novos no MESMO servidor do overlay (porta 8765, `vtuber_overlay.
    py`): `GET /vts/expressoes` (lista real) e `POST /vts/expressao/<nome>`
    (ativa). Ponto de acoplamento #2 da extração original (`_ativar_animacao`/
    `_buscar_expressoes_vts`)."""

    id = "gaia_animacoes_vts"
    rotulo_categoria = "🎭 Animações do VTube Studio"

    def __init__(self):
        self._rotulo_para_arquivo = {}

    def esta_disponivel(self):
        return _porta_responde(URL_BASE_OVERLAY)

    def listar_subitens(self):
        try:
            with urllib.request.urlopen(URL_BASE_OVERLAY + "/vts/expressoes", timeout=2) as resp:
                arquivos = json.loads(resp.read())
        except Exception:
            arquivos = []
        if not arquivos:
            return ["⏳ VTube Studio não conectado"]
        self._rotulo_para_arquivo = {
            f"🎭 {a[:-len('.exp3.json')] if a.endswith('.exp3.json') else a}": a
            for a in arquivos
        }
        return list(self._rotulo_para_arquivo.keys())

    def executar(self, item):
        arquivo = self._rotulo_para_arquivo.get(item)
        if not arquivo:
            return

        def _chamar():
            try:
                rota = "/vts/expressao/" + urllib.parse.quote(arquivo, safe="")
                urllib.request.urlopen(urllib.request.Request(URL_BASE_OVERLAY + rota, method="POST"), timeout=2)
            except Exception:
                print(" [SISTEMA] IRIS (plugin GAIA): não consegui ativar a expressão - confira se a GAIA está rodando com o overlay ligado.")
        threading.Thread(target=_chamar, daemon=True).start()


class FuncoesGaiaProvider(ActionProvider):
    """FUNCIONAL (2026-08-21) - o original (`_abrir_funcao_gaia`) fazia uma
    chamada Python DIRETA em `PainelQt.instancia_atual` do MESMO processo;
    como o IRIS roda separado, isso agora passa pelo servidor HTTP novo do
    processo principal da GAIA (`integrations/iris_bridge.py`, porta 8766,
    sempre ativo - diferente do 8765 do overlay)."""

    id = "gaia_funcoes_gaia"
    rotulo_categoria = "⚙️ Funções da Gaia"

    def esta_disponivel(self):
        return _porta_responde(URL_BASE_BRIDGE)

    def listar_subitens(self):
        try:
            with urllib.request.urlopen(URL_BASE_BRIDGE + "/funcoes", timeout=2) as resp:
                return json.loads(resp.read())
        except Exception:
            return []

    def executar(self, item):
        def _chamar():
            try:
                corpo = json.dumps({"rotulo": item}).encode("utf-8")
                req = urllib.request.Request(
                    URL_BASE_BRIDGE + "/funcao", data=corpo, method="POST",
                    headers={"Content-Type": "application/json"},
                )
                urllib.request.urlopen(req, timeout=2)
            except Exception:
                print(" [SISTEMA] IRIS (plugin GAIA): não consegui abrir a função - confira se a GAIA está rodando.")
        threading.Thread(target=_chamar, daemon=True).start()

# 🔥 `AnimeTrackerProvider` mudou pra `iris_plugin_moirai` em 2026-08-24 - o
# Assistente de Animes deixou de ser hospedado pela GAIA (processo próprio,
# Project-MOIRAI, porta 8768) - ver ARQUITETURA.md e o TODO.md do plugin novo.
