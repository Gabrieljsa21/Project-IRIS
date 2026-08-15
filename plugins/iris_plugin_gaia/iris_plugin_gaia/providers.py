# -*- coding: utf-8 -*-
"""Os 4 `ActionProvider` que conectam o IRIS à GAIA. Ver `TODO.md` deste
pacote pro estado real de cada um - só `AvatarOverlayProvider` está
totalmente funcional hoje; os outros 3 são STUBS deliberados (documentados,
não escondidos) porque dependem de um endpoint/IPC do lado da GAIA que ainda
não existe (trabalho cross-repo, fora do escopo desta extração)."""

import os
import socket
import threading
import urllib.request

from iris.plugins.base import ActionProvider

# Base da API HTTP local do overlay (`vtuber_overlay.py`, porta 8765 - já
# existente na GAIA, sem nenhuma mudança necessária do lado dela).
# Sobrescrevível via variável de ambiente pra quem roda a GAIA numa porta
# diferente.
URL_BASE_OVERLAY = os.environ.get("IRIS_GAIA_OVERLAY_URL", "http://127.0.0.1:8765")

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
    """STUB - ver `TODO.md` deste pacote. A GAIA fala com o VTube Studio via
    `integrations.vtubestudio.vtube_studio_client.VTubeStudioClient`
    (websocket direto), não pela API HTTP do overlay - esse módulo mora no
    processo da GAIA, não é instalável separadamente por este plugin. Ponto
    de acoplamento #2 da extração original (`_ativar_animacao`/
    `_buscar_expressoes_vts`)."""

    id = "gaia_animacoes_vts"
    rotulo_categoria = "🎭 Animações do VTube Studio"

    def esta_disponivel(self):
        return False  # sempre indisponível até existir um endpoint HTTP do lado da GAIA - ver TODO.md

    def listar_subitens(self):
        return ["ℹ️ Ainda não implementado - ver TODO.md deste plugin"]

    def executar(self, item):
        return


class FuncoesGaiaProvider(ActionProvider):
    """STUB - ver `TODO.md` deste pacote. O original (`_abrir_funcao_gaia`)
    fazia uma chamada Python DIRETA em `PainelQt.instancia_atual` do MESMO
    processo - o IRIS roda num processo separado, então isso nunca funciona
    sem algum IPC novo do lado da GAIA (endpoint HTTP, named pipe, etc)."""

    id = "gaia_funcoes_gaia"
    rotulo_categoria = "⚙️ Funções da Gaia"

    def esta_disponivel(self):
        return False  # sempre indisponível até existir IPC do lado da GAIA - ver TODO.md

    def listar_subitens(self):
        return ["ℹ️ Ainda não implementado - ver TODO.md deste plugin"]

    def executar(self, item):
        return


class AnimeTrackerProvider(ActionProvider):
    """STUB - ver `TODO.md` deste pacote. O original (`_adicionar_anime_da_
    area_de_transferencia`/`_assistir_anime_por_titulo`) fala direto com
    `features.anime_tracker.anime_tracker` (scraping + qBittorrent), uma
    feature de produto da GAIA sem API HTTP nenhuma hoje."""

    id = "gaia_anime_tracker"
    rotulo_categoria = "🎬 Anime Tracker"

    def esta_disponivel(self):
        return False  # sempre indisponível até existir endpoint/IPC do lado da GAIA - ver TODO.md

    def listar_subitens(self):
        return ["ℹ️ Ainda não implementado - ver TODO.md deste plugin"]

    def executar(self, item):
        return
