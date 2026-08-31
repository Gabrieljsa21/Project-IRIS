# -*- coding: utf-8 -*-
"""`AnimeTrackerProvider` - extraído de `iris_plugin_gaia/providers.py`
(2026-08-24) quando o Assistente de Animes deixou de ser hospedado pela GAIA
e ganhou processo próprio (Project-MOIRAI, porta 8768). Mesmo contrato HTTP
de sempre (`/anime/para_assistir`, `/anime/adicionar`, `/anime/assistir/
<titulo>`) - só a URL base mudou, de `iris_plugin_gaia.providers.
URL_BASE_BRIDGE` (GAIA, porta 8766) pra aqui (MOIRAI, porta 8768).

🔥 Lista só "Para assistir" + capa como ícone (2026-08-24, pedido do
usuário): antes listava TODO "tenho_interesse" com o emoji "🎬" genérico pra
todo mundo - clicar num título sem nada baixado ainda era um clique morto
(sem seletor de episódio aqui, diferente do Painel da GAIA). Agora só entra
quem `/anime/para_assistir` devolve (já filtrado pelo MOIRAI, ver
`moirai/core/anime_tracker.py::obter_titulos_para_assistir`), e cada um
ganha a própria capa como ícone (`icone_para_subitem`, ver `iris/plugins/
base.py`) - baixada 1x via `/anime/capa/<chave>?url=<capa_url>` (o MOIRAI
devolve os BYTES, nunca um caminho local - processo/pasta diferentes) e
cacheada em disco aqui do lado do IRIS, em BACKGROUND (nunca dentro de
`listar_subitens`, que roda na hora de abrir a categoria - baixar capa
síncrona ali travaria o popup até a rede responder)."""

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

PASTA_CAPAS_CACHE = os.path.join("data", "moirai_capas_cache")


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


def _caminho_capa_cacheada(chave, capa_url):
    """Só a parte SÍNCRONA/rápida (sem rede) - caminho da capa se ela já
    estiver em cache local, ou None se ainda precisa baixar. Mesmo
    raciocínio de `anime_tracker.capa_local_cacheada` do lado do MOIRAI."""
    if not chave or not capa_url:
        return None
    extensao = os.path.splitext(capa_url.split("?")[0])[1] or ".jpg"
    caminho = os.path.join(PASTA_CAPAS_CACHE, f"{chave}{extensao}")
    return caminho if os.path.exists(caminho) else None


def _baixar_e_cachear_capa(chave, capa_url):
    """Parte que FAZ REDE - sempre chamada numa thread própria (nunca no
    caminho síncrono de `listar_subitens`/`icone_para_subitem`, ambos lidos
    a cada repaint do popup). Passa pelo próprio MOIRAI (`/anime/capa/
    <chave>?url=<capa_url>`), nunca direto na URL original da capa - é o
    MOIRAI quem já tem a lógica de cache/User-Agent pra isso."""
    if not chave or not capa_url:
        return None
    extensao = os.path.splitext(capa_url.split("?")[0])[1] or ".jpg"
    caminho = os.path.join(PASTA_CAPAS_CACHE, f"{chave}{extensao}")
    try:
        rota = f"/anime/capa/{urllib.parse.quote(chave, safe='')}?url={urllib.parse.quote(capa_url, safe='')}"
        with urllib.request.urlopen(URL_BASE_MOIRAI + rota, timeout=8) as resp:
            dados = resp.read()
        os.makedirs(PASTA_CAPAS_CACHE, exist_ok=True)
        with open(caminho, "wb") as f:
            f.write(dados)
        return caminho
    except Exception:
        return None


class AnimeTrackerProvider(ActionProvider):
    """FUNCIONAL - fala direto com o Project-MOIRAI (processo próprio, dono
    do estado dos animes desde 2026-08-24)."""

    # 🔥 `id` continua "moirai_anime_tracker" de propósito (2026-08-30,
    # renomeado só o RÓTULO visível pra "Watchlist", pedido do usuário) - só
    # o texto exibido no popup mudou; `id` é usado internamente pra registro/
    # lookup (`iris/plugins/registry.py`) e não precisa acompanhar o nome de
    # exibição.
    id = "moirai_anime_tracker"
    rotulo_categoria = "🎬 Watchlist"

    def __init__(self):
        self._icones_por_subitem = {}

    def esta_disponivel(self):
        return _porta_responde(URL_BASE_MOIRAI)

    def listar_subitens(self):
        try:
            with urllib.request.urlopen(URL_BASE_MOIRAI + "/anime/para_assistir", timeout=2) as resp:
                animes = json.loads(resp.read())
        except Exception:
            animes = []

        if not animes:
            return ["ℹ️ Nenhum anime pronto pra assistir agora"]

        itens = [_ITEM_ACAO_ADICIONAR_ANIME]
        for anime in animes:
            item = f"🎬 {anime.get('titulo', '')}"
            itens.append(item)
            chave, capa_url = anime.get("chave"), anime.get("capa_url")
            caminho_cache = _caminho_capa_cacheada(chave, capa_url)
            if caminho_cache:
                self._icones_por_subitem[item] = caminho_cache
            elif chave and capa_url:
                threading.Thread(target=self._baixar_capa_em_fundo, args=(item, chave, capa_url), daemon=True).start()
        return itens

    def _baixar_capa_em_fundo(self, item, chave, capa_url):
        caminho = _baixar_e_cachear_capa(chave, capa_url)
        if caminho:
            self._icones_por_subitem[item] = caminho

    def icone_para_subitem(self, item):
        return self._icones_por_subitem.get(item)

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
