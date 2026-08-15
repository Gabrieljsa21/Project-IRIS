# -*- coding: utf-8 -*-
"""Menu Radial em PySide6 - popup circular com N anéis concêntricos
(favoritos SEMPRE visíveis no anel mais interno; clicar numa categoria empurra
mais um anel pra fora, sem fechar os anteriores) e cores vivas só na fatia em
destaque. Portado de `Project G.A.I.A/assistant/ui/menu_radial_qt.py` (ver
`ARQUITETURA.md` na raiz do repo pro histórico da extração e os 4 pontos de
acoplamento com a GAIA que saíram daqui).

Este popup é o CORE do IRIS - zero dependência de GAIA. Categorias extras
(Funções da Gaia, Avatar Overlay, Animações do VTube Studio, Anime Tracker)
não existem aqui: são registradas em runtime por um plugin opcional (ver
`iris/plugins/registry.py` e `plugins/iris_plugin_gaia/`), consultado só
através da interface `ActionProvider` (`iris/plugins/base.py`) - o popup
nunca importa nada de um plugin específico.

Disparado pelo hotkey GLOBAL (Ctrl+Alt+Espaço, registrado em `iris/main.py`)
via `mostrar_menu_radial_qt()` - chamado na thread do hook de teclado, por
isso `main.py` marshalla a chamada pra thread do Qt via `Signal.emit()` antes
de chamar isto (mesmo padrão documentado em `ARQUITETURA.md`)."""
import math
import os
import threading
from datetime import datetime

from PySide6.QtCore import Qt, QRectF, QTimer, QVariantAnimation, QEasingCurve
from PySide6.QtGui import (
    QPainter, QPainterPath, QColor, QConicalGradient, QRadialGradient, QFont,
    QPen, QBrush, QCursor, QGuiApplication, QImage, QPixmap,
)
from PySide6.QtWidgets import QWidget, QGraphicsBlurEffect, QGraphicsScene, QGraphicsPixmapItem

import iris.core.radial_menu as radial_menu
import iris.core.app_launcher as app_launcher_mod
import iris.core.hardware_monitor as hardware_monitor
from iris.plugins import registry as plugin_registry

# ---------------------------------------------------------------------------
# Geometria - ângulo 0° = 3h (leste), crescendo ANTI-horário (Qt); item 0 no
# topo (90°), os seguintes em sentido HORÁRIO (ângulo decrescente).
#
# O raio de cada nível é calculado (não fixo em 2 constantes) pra suportar
# categorias aninhadas dentro de categorias. Nível 0 = anel de favoritos
# (sempre visível); nível 1, 2, 3... = cada categoria aberta a partir do nível
# anterior. `MAX_NIVEIS_ANINHADOS` limita a profundidade (sanidade visual/
# tamanho de tela, não uma limitação técnica de verdade).
# ---------------------------------------------------------------------------
RAIO_INTERNO = 68          # borda interna do anel de favoritos / raio do centro
RAIO_EXTERNO_1 = 176       # borda externa do anel de favoritos (nível 0, sempre visível)
GAP_ENTRE_ANEIS = 18       # folga visual entre um anel e o próximo
LARGURA_ANEL_SUBITENS = 110  # espessura de cada anel ALÉM do primeiro (subitens/categorias aninhadas)
MAX_NIVEIS_ANINHADOS = 4  # favoritos (nível 0) + até 3 categorias aninhadas
MARGEM = 80
CRESCIMENTO_HOVER = 14
GAP_GRAUS = 3


def _raio_interno_nivel(indice_nivel):
    if indice_nivel <= 0:
        return RAIO_INTERNO
    raio = RAIO_EXTERNO_1
    for _ in range(indice_nivel - 1):
        raio += GAP_ENTRE_ANEIS + LARGURA_ANEL_SUBITENS
    return raio + GAP_ENTRE_ANEIS


def _raio_externo_nivel(indice_nivel):
    if indice_nivel <= 0:
        return RAIO_EXTERNO_1
    return _raio_interno_nivel(indice_nivel) + LARGURA_ANEL_SUBITENS


def _tamanho_para_profundidade(profundidade):
    """profundidade = quantos anéis além do de favoritos estão abertos AGORA
    (`len(self.pilha)`) - o popup só ocupa na tela o espaço que precisa neste
    momento, cresce/encolhe conforme o usuário entra/sai de categorias."""
    return _raio_externo_nivel(profundidade) * 2 + MARGEM


def _profundidade_maxima_configurada(favoritos_atuais):
    """Quantos anéis de categoria-dentro-de-categoria são ALCANÇÁVEIS de
    verdade a partir dos favoritos ATUAIS - não o teto técnico
    (`MAX_NIVEIS_ANINHADOS`, que só limita o quanto DÁ pra aninhar) nem
    "quantas categorias existem no sistema" (uma categoria que existe mas
    não está favoritada agora não é alcançável nesta sessão do popup - a
    lista de favoritos não muda sem recriar o popup). Se não há NENHUMA
    categoria favoritada, o popup nunca vai abrir um 2º anel - reservar
    margem pra isso seria espaço 100% desperdiçado. Só categorias PRÓPRIAS
    do usuário aninham mais categorias dentro - categorias de plugin e os 3
    itens especiais (Pastas/Recentes/Steam) sempre abrem uma lista achatada,
    nunca um anel mais fundo."""
    categorias = radial_menu.obter_categorias()
    nomes_categoria = set(categorias.keys())
    categorias_planas = set(CATEGORIAS.keys()) | set(_categorias_plugins_disponiveis().keys())
    todas_categorias = nomes_categoria | categorias_planas

    def _profundidade(nome, visitados):
        if nome in categorias_planas:
            return 1
        if nome not in nomes_categoria or nome in visitados:
            return 0  # não é categoria, ou ciclo (A contém B, B contém A)
        visitados = visitados | {nome}
        itens = categorias.get(nome, {}).get("itens", [])
        sub_categorias = [it for it in itens if it in todas_categorias]
        if not sub_categorias:
            return 1
        return 1 + max(_profundidade(sub, visitados) for sub in sub_categorias)

    categorias_favoritadas = [f for f in favoritos_atuais if f in todas_categorias]
    if not categorias_favoritadas:
        return 0
    profundidade_real = max(_profundidade(nome, frozenset()) for nome in categorias_favoritadas)
    return min(profundidade_real, MAX_NIVEIS_ANINHADOS - 1)


def _margem_ancora_que_cabe(dimensao_tela, profundidade_desejada):
    """Quanto de margem reservar num eixo pro popup nunca precisar "pular"
    de lugar ao crescer até `profundidade_desejada` (ver
    `_profundidade_maxima_configurada`) - se isso não couber em metade da
    tela (comum no eixo Y de monitores widescreen, quando a config tem
    bastante aninhamento de verdade), recua pra profundidades menores até
    achar uma que caiba; no pior caso usa só o tamanho de favoritos
    (profundidade 0), aceitando que aninhar bem fundo perto da borda pode
    cortar um pouco, em troca do popup pelo menos abrir onde o cursor
    está."""
    for profundidade in range(profundidade_desejada, -1, -1):
        margem = _tamanho_para_profundidade(profundidade) // 2
        if margem <= dimensao_tela // 2:
            return margem
    return _tamanho_para_profundidade(0) // 2

# A paleta de cor é uma RODA DE COR CONTÍNUA: a cor de uma fatia em destaque
# vem do ÂNGULO ABSOLUTO dela na tela (matiz = função do ângulo), não de um
# índice fixo - a sequência sempre segue a ordem do arco-íris ao redor do
# círculo, se ajustando sozinha a QUALQUER quantidade de itens, sem repetir
# nem pular cores. Como um anel aninhado fica CENTRALIZADO no ângulo do botão
# que abriu ele (ver `_referencia_nivel`), a cor dos itens desse anel
# automaticamente fica parecida com a cor do botão pai.
_SATURACAO_CORES = 0.80
_VALOR_CORES = 0.97


def _cor_por_angulo(angulo_absoluto):
    matiz = ((90 - angulo_absoluto) % 360) / 360.0
    return QColor.fromHsvF(matiz, _SATURACAO_CORES, _VALOR_CORES)


COR_NEUTRA = QColor("#3f4759")
COR_FAVORITO = QColor("#facc15")

# Abreviações de dia da semana/mês em PT-BR pro texto central do popup -
# `strftime` com "%a"/"%b" usa o locale padrão do processo, que é o C/inglês
# (depender de locale instalado é frágil, muda de sistema pra sistema no
# Windows) - mais simples e confiável escrever a tabela na mão.
DIAS_SEMANA_ABREV = ("Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom")
MESES_ABREV = ("Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez")

ICONES_FIXOS = {
    "bloco de notas": "📝",
    "calculadora": "🧮",
    "youtube": "▶️",
    "navegador": "🌐",
    "mixer de volume": "🎚️",
    "som": "🔊",
    "tela": "🖥️",
}
ICONE_PADRAO = "🎮"
# Fatia de paginação - sentinela puramente de UI (não é persistido em lugar
# nenhum), gerada em runtime por `_paginar` sempre que uma camada não cabe
# inteira no limite configurado. Clicar avança a página (cíclico).
ITEM_MAIS_PAGINA = "▸ Mais"
ICONES_PASTA = ("📂", "📁")

# ---------------------------------------------------------------------------
# Categorias com conteúdo resolvido em runtime (valor None - ver
# `_subitens_de`). Categorias GENÉRICAS criadas pelo usuário
# (`radial_menu.obter_categorias()`) não entram aqui, são consultadas à parte
# - uma categoria genérica pode conter OUTRA categoria genérica como item,
# permitindo aninhar mais de 1 nível. Categorias de um PLUGIN (ver
# `iris.plugins.registry`) também não entram aqui - são consultadas em
# runtime via `plugin_registry.providers_disponiveis()`.
# ---------------------------------------------------------------------------
CATEGORIAS = {
    radial_menu.ITEM_PASTAS: None,
    radial_menu.ITEM_RECENTES: None,
    radial_menu.ITEM_STEAM: None,
}

# Linhas informativas (sem ação) usadas quando uma categoria dinâmica não tem
# nada de verdade pra mostrar ainda - reconhecidas por `_executar_item` pra
# não tentar "executar" um aviso.
_PREFIXOS_INFO = ("ℹ️", "⏳")

_CACHE_PIXMAPS_ICONE = {}


def _carregar_pixmap_icone(caminho):
    """Carrega e cacheia (processo inteiro, não só o popup atual) o ícone
    real de um jogo da Steam - decodificar a imagem toda vez que o popup
    redesenha (o relógio bate a cada 1s) seria desperdício. None se o arquivo
    não existir/não for uma imagem válida - quem chama cai pro emoji
    genérico nesse caso."""
    if not caminho:
        return None
    if caminho not in _CACHE_PIXMAPS_ICONE:
        pixmap = QPixmap(caminho)
        if pixmap.isNull():
            _CACHE_PIXMAPS_ICONE[caminho] = None
        else:
            _CACHE_PIXMAPS_ICONE[caminho] = pixmap.scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    return _CACHE_PIXMAPS_ICONE[caminho]


def _capacidade_nivel(indice_nivel):
    """Quantas fatias CABEM no anel desse nível, independente de quantas
    existem de verdade agora - o limite configurado é o próprio tamanho fixo
    da fatia (ver `_fatia_no_anel`), nível 0 é o anel de favoritos."""
    if indice_nivel <= 0:
        return radial_menu.obter_limite_por_camada_favoritos()
    return radial_menu.obter_limite_por_camada_subitens()


def _categorias_plugins_disponiveis():
    return {p.rotulo_categoria: p for p in plugin_registry.providers_disponiveis()}


def _e_categoria(rotulo):
    return (
        rotulo in CATEGORIAS
        or rotulo in radial_menu.obter_categorias()
        or rotulo in _categorias_plugins_disponiveis()
    )


def _categoria_favoritavel(categoria):
    """Categorias cujos SUBITENS são, eles mesmos, coisas que fazem sentido
    favoritar direto no anel de favoritos (apps/pastas) - habilita o
    favoritar por clique do meio dentro do submenu. Categorias de AÇÃO
    (fornecidas por um plugin) ficam de fora por padrão, a não ser que o
    provider marque `subitens_favoritaveis()` como True. Categorias genéricas
    do usuário entram aqui SEMPRE (mesmo aninhadas) - um item dentro delas é
    sempre um app/pasta/outra categoria, nunca uma ação."""
    if categoria in (radial_menu.ITEM_PASTAS, radial_menu.ITEM_RECENTES, radial_menu.ITEM_STEAM):
        return True
    if categoria in radial_menu.obter_categorias():
        return True
    provider = plugin_registry.provider_por_categoria(categoria)
    return bool(provider and provider.subitens_favoritaveis())


def _rotulo_exibicao_app(rotulo):
    """Padroniza a capitalização de nomes de app pra exibição - apps
    escaneados (`iris/core/apps_scanner.py`) são salvos com a chave toda em
    minúsculo, o que faria "Discord"/"Steam"/"Spotify" aparecerem como
    "discord"/"steam"/"spotify" no menu. Só afeta a EXIBIÇÃO - a chave de
    verdade usada pra abrir o app continua intacta."""
    return rotulo.title()


def _favoritos_efetivos():
    """Favoritos do perfil atual, sem os que estão numa categoria DESATIVADA
    ou desativados individualmente - continuam na posição salva em
    `obter_favoritos()` (pra reaparecer no mesmo lugar ao reativar), só não
    aparecem no popup enquanto desligados."""
    favoritos = list(radial_menu.obter_favoritos())
    categorias = radial_menu.obter_categorias()
    desativados_fav = radial_menu.obter_favoritos_desativados()
    return [
        f for f in favoritos
        if not (f in categorias and not categorias[f].get("ativa", True))
        and f not in desativados_fav
    ]


def _dividir_icone_rotulo(rotulo):
    partes = rotulo.split(" ", 1)
    if partes[0] and ord(partes[0][0]) > 127:
        return partes[0], (partes[1] if len(partes) > 1 else "")
    return None, rotulo


def _angulo_item(indice, capacidade, referencia=90.0):
    """Ângulo central da fatia `indice` - `referencia` é onde a fatia 0 fica
    (90° = topo, comportamento padrão do anel de favoritos). Um anel aberto a
    partir de uma categoria usa uma `referencia` diferente de 90°
    (ver `RadialMenuQt._referencia_nivel`), fazendo os itens dele ficarem
    centrados em volta de onde o botão que os abriu está na tela."""
    passo = 360.0 / capacidade
    return (referencia - indice * passo) % 360


def _indice_da_fatia(angulo, capacidade, referencia=90.0):
    """Cada fatia é DESENHADA centrada em `_angulo_item` (de `centro -
    passo/2` até `centro + passo/2`) - o hit-test usa `round()` (não
    `floor()`) pra centralizar a área clicável no mesmo ponto que o desenho
    já usa."""
    passo = 360.0 / capacidade
    deslocado = (referencia - angulo) % 360
    return round(deslocado / passo) % capacidade


def _fatia_no_anel(dx, dy, raio_min, raio_max, capacidade, quantidade_real, referencia=90.0):
    """O TAMANHO de cada fatia (`capacidade`, o limite configurado daquele
    anel) é fixo, independente de quantos itens existem de verdade agora
    (`quantidade_real`) - uma categoria com só 3 itens ocupa 3 fatias do
    TAMANHO PADRÃO (deixando o resto do círculo vazio), em vez de esticar
    essas 3 fatias pra preencher o círculo inteiro. Um clique/hover que caia
    numa posição "vazia" (índice >= quantidade_real) não acerta nada."""
    distancia = math.hypot(dx, dy)
    if distancia > raio_max or distancia < raio_min:
        return None
    angulo = math.degrees(math.atan2(-dy, dx)) % 360
    indice = _indice_da_fatia(angulo, capacidade, referencia)
    return indice if indice < quantidade_real else None


class RadialMenuQt(QWidget):
    def __init__(self):
        super().__init__()
        self.favoritos_completos = _favoritos_efetivos()
        self.pagina_1 = 0
        self.total_paginas_1 = 1
        self.rotulos = []
        self.n = 0

        # Pilha de níveis ABERTOS além do de favoritos; pilha[0] = 1º anel
        # aberto (clicando uma categoria em favoritos), pilha[1] = 2º anel
        # (clicando uma categoria DENTRO do 1º), etc. Cada entrada:
        # {"categoria": rótulo que abriu este nível, "completos": [...],
        #  "exibidos": [...], "pagina": 0, "total_paginas": 1, "hover": None}.
        self.pilha = []

        self.filtro_busca = ""

        self.indice_hover = None            # hover no anel de FAVORITOS (nível 0)
        self.crescimento_atual = {}         # (chave_nivel, indice) -> px crescidos
        self.animacoes = {}

        self._arrastando_indice = None      # índice sendo arrastado no anel de favoritos (Alt+arrastar), ou None
        self._ancora_tela = None            # (cx, cy) fixo - o popup só REDIMENSIONA em volta dele, nunca se move
        self.tamanho_atual = _tamanho_para_profundidade(0)

        # Ícones reais dos jogos da Steam - lidos 1x aqui (não a cada
        # redesenho, que roda toda hora por causa do relógio).
        self._icones_steam = app_launcher_mod.obter_icones_jogos_steam()

        self._recalcular_exibidos()

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self._reposicionar_para_profundidade()

        self.metricas = {"cpu_percent": None, "ram_percent": None, "gpu_percent": None}
        self._buscar_metricas_async()
        self._timer_metricas = QTimer(self)
        self._timer_metricas.timeout.connect(self._buscar_metricas_async)
        # 8s - cada tick cria uma thread + um subprocess nvidia-smi
        # (obter_metricas_sistema); o popup normalmente fica aberto pouco
        # tempo, 8s já é granularidade suficiente pro mostrador de CPU/RAM/GPU
        # sem dobrar o custo de subprocess à toa.
        self._timer_metricas.start(8000)

        self._timer_relogio = QTimer(self)
        self._timer_relogio.timeout.connect(self.update)
        self._timer_relogio.start(1000)

    # ------------------------------------------------------------------
    # Janela dinâmica - só ocupa o espaço que a profundidade atual precisa,
    # crescendo/encolhendo em volta de uma ÂNCORA fixa (o ponto onde o cursor
    # estava ao abrir, já clampado pro tamanho MÁXIMO possível) - assim o
    # popup nunca "pula" de posição ao abrir/fechar um nível, só muda de
    # tamanho ao redor do mesmo centro.
    # ------------------------------------------------------------------
    def _reposicionar_para_profundidade(self):
        if self._ancora_tela is None:
            cursor_pos = QCursor.pos()
            # `screenAt(cursor_pos)` acha o monitor que contém o cursor AGORA
            # (em vez de sempre abrir no monitor primário, ignorando onde o
            # mouse estava de verdade em setups com mais de 1 monitor).
            tela_atual = QGuiApplication.screenAt(cursor_pos) or QGuiApplication.primaryScreen()
            tela = tela_atual.geometry()
            # Margem por EIXO, não uma única pros dois - a altura de um monitor
            # comum não comporta a mesma margem que a largura (ver
            # `_margem_ancora_que_cabe`). E baseada no que está REALMENTE
            # configurado agora, não no teto técnico (ver
            # `_profundidade_maxima_configurada`).
            profundidade_desejada = _profundidade_maxima_configurada(self.favoritos_completos)
            margem_x = _margem_ancora_que_cabe(tela.width(), profundidade_desejada)
            margem_y = _margem_ancora_que_cabe(tela.height(), profundidade_desejada)
            cx = max(tela.left() + margem_x, min(cursor_pos.x(), tela.right() - margem_x))
            cy = max(tela.top() + margem_y, min(cursor_pos.y(), tela.bottom() - margem_y))
            self._ancora_tela = (cx, cy)

        tamanho = _tamanho_para_profundidade(len(self.pilha))
        self.tamanho_atual = tamanho
        self.setFixedSize(tamanho, tamanho)
        cx, cy = self._ancora_tela
        self.move(int(cx - tamanho / 2), int(cy - tamanho / 2))

    # ------------------------------------------------------------------
    # Busca / paginação
    # ------------------------------------------------------------------
    def _aplicar_filtro(self, lista):
        if not self.filtro_busca:
            return lista
        q = self.filtro_busca.lower()

        def _corresponde(r):
            if q in _dividir_icone_rotulo(r)[1].lower() or q in r.lower():
                return True
            apelido = radial_menu.obter_apelido(r)
            return bool(apelido and q in apelido.lower())
        return [r for r in lista if _corresponde(r)]

    def _paginar(self, lista, pagina, limite):
        """Quando não cabe tudo numa página, a ÚLTIMA posição vira
        `ITEM_MAIS_PAGINA` (avança a página, com wraparound), reservando 1
        vaga real a menos por página (`tamanho_pagina = limite - 1`) pra o
        total de fatias visíveis nunca passar do limite configurado."""
        if len(lista) <= limite:
            return lista, 0, 1
        tamanho_pagina = max(1, limite - 1)
        total_paginas = math.ceil(len(lista) / tamanho_pagina)
        pagina = pagina % total_paginas
        inicio = pagina * tamanho_pagina
        pagina_atual = lista[inicio:inicio + tamanho_pagina]
        pagina_atual.append(ITEM_MAIS_PAGINA)
        return pagina_atual, pagina, total_paginas

    def _recalcular_nivel(self, indice_pilha):
        nivel = self.pilha[indice_pilha]
        filtrados = self._aplicar_filtro(nivel["completos"])
        limite = radial_menu.obter_limite_por_camada_subitens()
        nivel["exibidos"], nivel["pagina"], nivel["total_paginas"] = self._paginar(filtrados, nivel["pagina"], limite)
        nivel["hover"] = None

    def _recalcular_exibidos(self):
        filtrados1 = self._aplicar_filtro(self.favoritos_completos)
        self.rotulos, self.pagina_1, self.total_paginas_1 = self._paginar(filtrados1, self.pagina_1, radial_menu.obter_limite_por_camada_favoritos())
        self.n = len(self.rotulos)
        self.indice_hover = None
        self.crescimento_atual = {}
        for i in range(len(self.pilha)):
            self._recalcular_nivel(i)
        self._atualizar_hover_cursor_atual()

    def _cadeia_categorias_atual(self):
        """Nomes de categoria já abertos AGORA em qualquer ponto da pilha -
        proteção contra ciclo (categoria A contém B, B contém A de volta):
        nunca deixa empilhar uma categoria que já está aberta em algum nível
        do caminho atual."""
        return {n["categoria"] for n in self.pilha}

    def _referencia_nivel(self, indice_nivel, quantidade_exibida):
        """Ângulo onde a fatia 0 desse anel fica - 90° (topo) pro anel de
        favoritos (nível 0, sem "pai"); pros demais, CENTRALIZADO em volta do
        ângulo onde o botão que abriu esse nível está na tela. Sem âncora
        salva (não deveria acontecer pra nível >= 1, mas não trava se
        acontecer), cai no comportamento antigo (topo)."""
        if indice_nivel <= 0:
            return 90.0
        ancora = self.pilha[indice_nivel - 1].get("angulo_ancora")
        if ancora is None:
            return 90.0
        passo = 360.0 / _capacidade_nivel(indice_nivel)
        return (ancora + (quantidade_exibida - 1) * passo / 2) % 360

    def _empilhar_categoria(self, categoria, angulo_ancora=None):
        radial_menu.registrar_uso(categoria)
        nivel = {"categoria": categoria, "completos": self._subitens_de(categoria), "exibidos": [], "pagina": 0, "total_paginas": 1, "hover": None, "angulo_ancora": angulo_ancora}
        self.pilha.append(nivel)
        self._recalcular_nivel(len(self.pilha) - 1)
        self._reposicionar_para_profundidade()
        self._atualizar_hover_cursor_atual()

    def wheelEvent(self, event):
        delta = 1 if event.angleDelta().y() < 0 else -1
        pos = event.position()
        cx = cy = self.tamanho_atual / 2
        distancia = math.hypot(pos.x() - cx, pos.y() - cy)

        if RAIO_INTERNO <= distancia <= RAIO_EXTERNO_1:
            if self.total_paginas_1 > 1:
                self.pagina_1 += delta
                self._recalcular_exibidos()
                self.update()
            return

        for indice_nivel in range(len(self.pilha), 0, -1):
            r_int = _raio_interno_nivel(indice_nivel)
            r_ext = _raio_externo_nivel(indice_nivel)
            if r_int <= distancia <= r_ext:
                nivel = self.pilha[indice_nivel - 1]
                if nivel["total_paginas"] > 1:
                    nivel["pagina"] += delta
                    self._recalcular_nivel(indice_nivel - 1)
                    self._atualizar_hover_cursor_atual()
                return

    def _buscar_metricas_async(self):
        def _trabalho():
            m = hardware_monitor.obter_metricas_sistema()
            self.metricas = m
            self.update()
        threading.Thread(target=_trabalho, daemon=True).start()

    def _subitens_de(self, categoria):
        if categoria == radial_menu.ITEM_PASTAS:
            pastas = radial_menu.obter_pastas()
            if not pastas:
                return ["ℹ️ Nenhuma pasta configurada (Configurações > Pastas)"]
            return [f"📁 {nome}" for nome in pastas.keys()]
        if categoria == radial_menu.ITEM_RECENTES:
            recentes = radial_menu.obter_recentes()
            if not recentes:
                return ["ℹ️ Nada usado ainda"]
            return list(recentes)
        if categoria == radial_menu.ITEM_STEAM:
            jogos_instalados = app_launcher_mod.listar_jogos_steam_instalados()
            ordem = radial_menu.mesclar_ordem_steam(jogos_instalados)
            desativados = radial_menu.obter_steam_desativados()
            jogos = [j for j in ordem if j not in desativados]
            if not jogos:
                return ["ℹ️ Nenhum jogo da Steam ativo (escaneie/ative em Configurações > Steam)"]
            return jogos
        provider = plugin_registry.provider_por_categoria(categoria)
        if provider:
            try:
                return provider.listar_subitens() or ["ℹ️ Nada disponível agora"]
            except Exception:
                return ["ℹ️ Erro ao consultar este plugin"]
        categorias_usuario = radial_menu.obter_categorias()
        if categoria in categorias_usuario:
            itens = categorias_usuario[categoria].get("itens", [])
            desativados = set(categorias_usuario[categoria].get("itens_desativados", []))
            return [i for i in itens if i not in desativados]
        return CATEGORIAS.get(categoria) or []

    def _iniciar_animacao(self, chave, destino):
        anim_antiga = self.animacoes.get(chave)
        if anim_antiga:
            anim_antiga.stop()
        origem = self.crescimento_atual.get(chave, 0)
        anim = QVariantAnimation(self)
        anim.setStartValue(float(origem))
        anim.setEndValue(float(destino))
        anim.setDuration(180)
        anim.setEasingCurve(QEasingCurve.OutCubic)

        def _aplicar(valor, c=chave):
            self.crescimento_atual[c] = valor
            self.update()

        anim.valueChanged.connect(_aplicar)
        anim.start()
        self.animacoes[chave] = anim

    def _atualizar_hover(self, pos):
        """Recalcula qual fatia está sob `pos` (coordenadas locais do popup),
        em favoritos e em qualquer nível aberto - também precisa ser chamado
        depois de QUALQUER mudança de conteúdo que não vem de um movimento de
        mouse de verdade (paginar clicando "▸ Mais", abrir uma categoria,
        rolar o scroll, digitar na busca): sem isso, se o conteúdo de um anel
        muda mas o cursor não se move nem 1px, o Qt nunca dispara
        `mouseMoveEvent` de novo, e o destaque de hover fica "grudado" na
        posição antiga mesmo já mostrando um item diferente ali."""
        cx = cy = self.tamanho_atual / 2
        dx, dy = pos.x() - cx, pos.y() - cy

        indice_1 = _fatia_no_anel(dx, dy, RAIO_INTERNO, RAIO_EXTERNO_1, _capacidade_nivel(0), self.n)
        if indice_1 != self.indice_hover:
            anterior = self.indice_hover
            self.indice_hover = indice_1
            if anterior is not None:
                self._iniciar_animacao(("n0", anterior), 0)
            if indice_1 is not None:
                self._iniciar_animacao(("n0", indice_1), CRESCIMENTO_HOVER)

        for indice_nivel in range(1, len(self.pilha) + 1):
            nivel = self.pilha[indice_nivel - 1]
            n_nivel = len(nivel["exibidos"])
            referencia_nivel = self._referencia_nivel(indice_nivel, n_nivel)
            indice = _fatia_no_anel(dx, dy, _raio_interno_nivel(indice_nivel), _raio_externo_nivel(indice_nivel), _capacidade_nivel(indice_nivel), n_nivel, referencia_nivel) if n_nivel else None
            if indice != nivel["hover"]:
                anterior = nivel["hover"]
                nivel["hover"] = indice
                chave = f"n{indice_nivel}"
                if anterior is not None:
                    self._iniciar_animacao((chave, anterior), 0)
                if indice is not None:
                    self._iniciar_animacao((chave, indice), CRESCIMENTO_HOVER)

    def _atualizar_hover_cursor_atual(self):
        self._atualizar_hover(self.mapFromGlobal(QCursor.pos()))
        self.update()

    def _atualizar_icone_cursor(self, alt_pressionado):
        """Mãozinha aberta com Alt segurado sobre o popup, fechada durante o
        arrasto de verdade, seta normal o resto do tempo."""
        if self._arrastando_indice is not None:
            self.setCursor(Qt.ClosedHandCursor)
        elif alt_pressionado:
            self.setCursor(Qt.OpenHandCursor)
        else:
            self.unsetCursor()

    def mouseMoveEvent(self, event):
        pos = event.position()
        self._atualizar_icone_cursor(bool(event.modifiers() & Qt.AltModifier))

        if self._arrastando_indice is not None:
            # Alt+arrastar reordenando ao vivo - troca o item arrastado de
            # lugar com o que estiver embaixo do cursor agora, na hora, sem
            # esperar soltar o botão.
            cx = cy = self.tamanho_atual / 2
            dx, dy = pos.x() - cx, pos.y() - cy
            indice_alvo = _fatia_no_anel(dx, dy, RAIO_INTERNO, RAIO_EXTERNO_1, _capacidade_nivel(0), self.n)
            self.indice_hover = self._arrastando_indice
            if indice_alvo is not None and indice_alvo != self._arrastando_indice:
                self.rotulos[self._arrastando_indice], self.rotulos[indice_alvo] = self.rotulos[indice_alvo], self.rotulos[self._arrastando_indice]
                self.favoritos_completos = list(self.rotulos)
                self._arrastando_indice = indice_alvo
            self.update()
            return

        self._atualizar_hover(pos)

    def mousePressEvent(self, event):
        cx = cy = self.tamanho_atual / 2
        pos = event.position()
        dx, dy = pos.x() - cx, pos.y() - cy

        if event.button() == Qt.LeftButton and event.modifiers() & Qt.AltModifier:
            indice_1 = _fatia_no_anel(dx, dy, RAIO_INTERNO, RAIO_EXTERNO_1, _capacidade_nivel(0), self.n)
            if indice_1 is not None:
                # `self.rotulos` é só o que está VISÍVEL agora - se algum
                # favorito estiver oculto (busca ativa, paginado, desativado,
                # ou dentro de uma categoria desativada), ele não está em
                # `self.rotulos` e seria APAGADO da lista real ao salvar.
                # Comparar com `radial_menu.obter_favoritos()` (a lista BRUTA
                # salva, sem nenhum filtro) - não com `self.favoritos_completos`,
                # que já vem filtrada e por isso nunca detectaria um item
                # desativado faltando.
                if self.filtro_busca or self.total_paginas_1 > 1 or len(self.rotulos) != len(radial_menu.obter_favoritos()):
                    print(" [SISTEMA] Menu Radial: arrastar pra reordenar só funciona sem busca ativa, com todos os favoritos numa página só e nenhum desativado (reordene em Configurações nesses casos).")
                    return
                self._arrastando_indice = indice_1
                self._atualizar_icone_cursor(True)
                return

        # Do anel mais EXTERNO (aberto por último) pro mais interno - clique
        # no anel visível na frente tem prioridade.
        for indice_nivel in range(len(self.pilha), 0, -1):
            nivel = self.pilha[indice_nivel - 1]
            itens = nivel["exibidos"]
            n_nivel = len(itens)
            referencia_nivel = self._referencia_nivel(indice_nivel, n_nivel)
            indice = _fatia_no_anel(dx, dy, _raio_interno_nivel(indice_nivel), _raio_externo_nivel(indice_nivel), _capacidade_nivel(indice_nivel), n_nivel, referencia_nivel) if n_nivel else None
            if indice is None:
                continue
            item = itens[indice]
            if item == ITEM_MAIS_PAGINA:
                if event.button() == Qt.LeftButton:
                    nivel["pagina"] += 1
                    self._recalcular_nivel(indice_nivel - 1)
                    self._atualizar_hover_cursor_atual()
                return
            if item.startswith(_PREFIXOS_INFO):
                return
            if event.button() == Qt.MiddleButton:
                if _categoria_favoritavel(nivel["categoria"]):
                    self._alternar_favorito(item)
                return
            if event.button() != Qt.LeftButton:
                return
            if _e_categoria(item) and len(self.pilha) < MAX_NIVEIS_ANINHADOS - 1 and item not in self._cadeia_categorias_atual():
                # Categoria (inclusive aninhada) - descarta qualquer coisa
                # ALÉM deste nível e empilha mais um, sem fechar os
                # anteriores ("manter os grupos sempre visíveis e ir
                # trocando os subgrupos").
                self.pilha = self.pilha[:indice_nivel]
                angulo_ancora = _angulo_item(indice, _capacidade_nivel(indice_nivel), referencia_nivel)
                self._empilhar_categoria(item, angulo_ancora=angulo_ancora)
                self.update()
                return
            self.close()
            self._executar_item(nivel["categoria"], item)
            return

        indice_1 = _fatia_no_anel(dx, dy, RAIO_INTERNO, RAIO_EXTERNO_1, _capacidade_nivel(0), self.n)
        if indice_1 is not None:
            rotulo = self.rotulos[indice_1]
            if rotulo == ITEM_MAIS_PAGINA:
                if event.button() == Qt.LeftButton:
                    self.pagina_1 += 1
                    self._recalcular_exibidos()
                    self.update()
                return
            if event.button() == Qt.MiddleButton:
                self._alternar_favorito(rotulo)
                return
            if event.button() != Qt.LeftButton:
                return
            if _e_categoria(rotulo):
                self.pilha = []
                angulo_ancora = _angulo_item(indice_1, _capacidade_nivel(0))
                self._empilhar_categoria(rotulo, angulo_ancora=angulo_ancora)
                self.update()
                return
            self.close()
            self._lancar(rotulo)
            return

        if event.button() == Qt.LeftButton:
            self.close()

    def mouseReleaseEvent(self, event):
        if self._arrastando_indice is not None:
            self._arrastando_indice = None
            radial_menu.salvar_favoritos(list(self.rotulos))
            self.favoritos_completos = _favoritos_efetivos()
            self._atualizar_icone_cursor(bool(event.modifiers() & Qt.AltModifier))
            self.update()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Alt:
            self._atualizar_icone_cursor(True)
            return
        if event.key() == Qt.Key_Escape:
            if self.filtro_busca:
                self.filtro_busca = ""
                self._recalcular_exibidos()
                self.update()
            else:
                self.close()
            return
        if event.key() == Qt.Key_Backspace:
            if self.filtro_busca:
                self.filtro_busca = self.filtro_busca[:-1]
                self.pagina_1 = 0
                for nivel in self.pilha:
                    nivel["pagina"] = 0
                self._recalcular_exibidos()
                self.update()
            return
        texto = event.text()
        if texto and (texto.isalnum() or texto == " "):
            self.filtro_busca += texto
            self.pagina_1 = 0
            for nivel in self.pilha:
                nivel["pagina"] = 0
            self._recalcular_exibidos()
            self.update()

    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key_Alt:
            self._atualizar_icone_cursor(False)

    def focusOutEvent(self, event):
        self.close()

    def showEvent(self, event):
        """Animação de abertura - fade-in simples via `setWindowOpacity`, sem
        mexer no fechamento (que continua instantâneo - fechar rápido de
        propósito é melhor UX que animar a saída)."""
        super().showEvent(event)
        self.setWindowOpacity(0.0)
        anim = QVariantAnimation(self)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setDuration(120)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        anim.valueChanged.connect(self.setWindowOpacity)
        anim.start()
        self._anim_abertura = anim

    def closeEvent(self, event):
        global _popup_atual
        if _popup_atual is self:
            _popup_atual = None
        if radial_menu.obter_ranking_automatico_ativo():
            radial_menu.ordenar_favoritos_por_uso()
        super().closeEvent(event)

    # ------------------------------------------------------------------
    # Favoritar/desfavoritar por clique do meio
    # ------------------------------------------------------------------
    def _alternar_favorito(self, rotulo):
        favoritos = radial_menu.obter_favoritos()
        if rotulo in favoritos:
            favoritos = [f for f in favoritos if f != rotulo]
            print(f" [SISTEMA] Menu Radial: '{rotulo}' removido dos favoritos.")
        else:
            favoritos = favoritos + [rotulo]
            print(f" [SISTEMA] Menu Radial: '{rotulo}' adicionado aos favoritos.")
        radial_menu.salvar_favoritos(favoritos)
        self.favoritos_completos = _favoritos_efetivos()
        self._recalcular_exibidos()
        self.update()

    def _lancar(self, rotulo):
        """Abre um app/pasta favoritado. Estendida pra pastas personalizadas."""
        icone, texto = _dividir_icone_rotulo(rotulo)
        if icone in ICONES_PASTA:
            caminho = radial_menu.obter_pastas().get(texto)
            if caminho and os.path.isdir(caminho):
                os.startfile(caminho)
                radial_menu.registrar_recente(rotulo)
                radial_menu.registrar_uso(rotulo)
            else:
                print(f" [SISTEMA] Menu Radial: pasta '{texto}' não encontrada/configurada (Configurações > Pastas).")
            return

        launcher = app_launcher_mod.AppLauncher()
        app_name, target = launcher.find_app(rotulo)
        if not app_name:
            print(f" [SISTEMA] Menu Radial: '{rotulo}' não foi encontrado (pode ter sido desinstalado - reescaneie os apps ou remova esse favorito).")
            return
        if app_name.lower() == "youtube":
            import webbrowser
            webbrowser.open("https://www.youtube.com")
        elif app_name.lower() == "navegador":
            import webbrowser
            webbrowser.open("https://www.google.com")
        else:
            launcher.open_app_cmd(app_name, target)
        radial_menu.registrar_recente(rotulo)
        radial_menu.registrar_uso(rotulo)

    def _executar_item(self, categoria_pai, item):
        provider = plugin_registry.provider_por_categoria(categoria_pai)
        if provider:
            try:
                provider.executar(item)
            except Exception as e:
                print(f" [SISTEMA] Menu Radial: erro executando '{item}' via plugin '{provider.id}': {e}")
            return
        # Pastas/Recentes/Steam/categorias genéricas (inclusive aninhadas) -
        # o item em si é um app/pasta lançável, mesma lógica de favoritos.
        self._lancar(item)

    def _path_fatia(self, cx, cy, raio_int, raio_ext, inicio_graus, extensao_graus):
        rect_ext = QRectF(cx - raio_ext, cy - raio_ext, raio_ext * 2, raio_ext * 2)
        rect_int = QRectF(cx - raio_int, cy - raio_int, raio_int * 2, raio_int * 2)
        path = QPainterPath()
        path.arcMoveTo(rect_ext, inicio_graus)
        path.arcTo(rect_ext, inicio_graus, extensao_graus)
        path.arcTo(rect_int, inicio_graus + extensao_graus, -extensao_graus)
        path.closeSubpath()
        return path

    def _desenhar_anel(self, painter, rotulos, capacidade, raio_int, raio_ext, hover_atual, chave_crescimento, resolver_icone_e_texto, todos_coloridos, mostrar_indicador_favorito=False, proxima_categoria=None, referencia=90.0):
        """`capacidade` - o TAMANHO de cada fatia (`passo`) é calculado a
        partir do limite configurado do anel, não da quantidade real de itens
        (`len(rotulos)`) - com menos itens que o limite, eles ocupam só uma
        fatia do tamanho padrão cada, deixando o resto do círculo vazio, em
        vez de esticar pra preencher tudo. `referencia` desloca onde a fatia 0
        fica - 90° (topo) pro anel de favoritos, ou o ângulo calculado por
        `_referencia_nivel` pra qualquer anel aberto a partir de uma
        categoria."""
        n = len(rotulos)
        if n == 0:
            return
        cx = cy = self.tamanho_atual / 2
        passo = 360.0 / capacidade

        paths_e_cores = []
        for i, rotulo in enumerate(rotulos):
            centro = _angulo_item(i, capacidade, referencia)
            inicio = centro - passo / 2 + GAP_GRAUS / 2
            extensao = passo - GAP_GRAUS
            crescimento = self.crescimento_atual.get((chave_crescimento, i), 0)
            path = self._path_fatia(cx, cy, raio_int, raio_ext + crescimento, inicio, extensao)
            destaque = todos_coloridos or (i == hover_atual) or (rotulo == proxima_categoria)
            cor = _cor_por_angulo(centro) if destaque else COR_NEUTRA
            paths_e_cores.append((path, cor, i, destaque))

        algum_destaque = any(d for _, _, _, d in paths_e_cores)
        if algum_destaque:
            glow_img = QImage(self.tamanho_atual, self.tamanho_atual, QImage.Format_ARGB32_Premultiplied)
            glow_img.fill(Qt.transparent)
            glow_painter = QPainter(glow_img)
            glow_painter.setRenderHint(QPainter.Antialiasing)
            for path, cor, i, destaque in paths_e_cores:
                if not destaque:
                    continue
                pen = QPen(cor, 7 if i == hover_atual else 4)
                glow_painter.setPen(pen)
                glow_painter.setBrush(Qt.NoBrush)
                glow_painter.drawPath(path)
            glow_painter.end()

            blur = QGraphicsBlurEffect()
            blur.setBlurRadius(26)
            scene = QGraphicsScene()
            item = QGraphicsPixmapItem(QPixmap.fromImage(glow_img))
            item.setGraphicsEffect(blur)
            scene.addItem(item)
            glow_borrado = QImage(self.tamanho_atual, self.tamanho_atual, QImage.Format_ARGB32_Premultiplied)
            glow_borrado.fill(Qt.transparent)
            p2 = QPainter(glow_borrado)
            p2.setRenderHint(QPainter.Antialiasing)
            scene.render(p2)
            p2.end()
            painter.drawImage(0, 0, glow_borrado)

        for path, cor, i, destaque in paths_e_cores:
            centro = _angulo_item(i, capacidade, referencia)
            if destaque:
                gradiente = QConicalGradient(cx, cy, centro - passo / 2)
                cor_escura = QColor(28, 28, 34, 235)
                cor_meio = QColor(min(255, cor.red() // 6 + 30), min(255, cor.green() // 6 + 30), min(255, cor.blue() // 6 + 34), 235)
                gradiente.setColorAt(0.0, cor_escura)
                gradiente.setColorAt(0.5, cor_meio)
                gradiente.setColorAt(1.0, cor_escura)
                painter.setBrush(QBrush(gradiente))
                painter.setPen(QPen(cor, 4 if i == hover_atual else 3))
            else:
                painter.setBrush(QBrush(QColor(32, 32, 38, 220)))
                painter.setPen(QPen(cor, 1.5))
            painter.drawPath(path)

        for i, rotulo in enumerate(rotulos):
            icone, texto = resolver_icone_e_texto(rotulo)
            centro = _angulo_item(i, capacidade, referencia)
            crescimento = self.crescimento_atual.get((chave_crescimento, i), 0)
            raio_texto = (raio_int + raio_ext) / 2 + crescimento / 2
            ang = math.radians(centro)
            tx = cx + raio_texto * math.cos(ang)
            ty = cy - raio_texto * math.sin(ang)
            largura = max(60, 2 * raio_texto * math.sin(math.radians(passo) / 2) - 6)

            if isinstance(icone, QPixmap):
                tam_icone = 44
                painter.drawPixmap(QRectF(tx - tam_icone / 2, ty - 34, tam_icone, tam_icone).toRect(), icone)
            else:
                painter.setPen(QColor("#f1efe9"))
                painter.setFont(QFont("Segoe UI Emoji", 14))
                painter.drawText(QRectF(tx - largura / 2, ty - 26, largura, 22), Qt.AlignCenter, icone)

            painter.setPen(QColor("#f1efe9"))
            painter.setFont(QFont("Segoe UI", 8, QFont.Bold))
            painter.drawText(QRectF(tx - largura / 2, ty, largura, 30), Qt.AlignCenter | Qt.TextWordWrap, texto)

            if mostrar_indicador_favorito and rotulo in self.favoritos_completos:
                painter.setPen(COR_FAVORITO)
                painter.setFont(QFont("Segoe UI", 9, QFont.Bold))
                raio_estrela = raio_ext + crescimento - 12
                ex = cx + raio_estrela * math.cos(ang)
                ey = cy - raio_estrela * math.sin(ang)
                painter.drawText(QRectF(ex - 10, ey - 10, 20, 20), Qt.AlignCenter, "★")

    def _resolver_item(self, rotulo, categoria_pai):
        """Resolve (ícone, texto) de QUALQUER item, em QUALQUER anel.
        `categoria_pai` é None pro anel de favoritos, ou o rótulo da categoria
        que abriu esse anel - usado só pra saber se um jogo da Steam pode
        aparecer aqui (o ícone real da Steam vale em qualquer contexto onde o
        nome bater, não só dentro da categoria "🎮 Steam")."""
        icone, texto = _dividir_icone_rotulo(rotulo)
        if icone is None:
            categorias_usuario = radial_menu.obter_categorias()
            if rotulo in categorias_usuario:
                icone = categorias_usuario[rotulo].get("icone") or "📁"
                texto = rotulo
            else:
                texto = _rotulo_exibicao_app(rotulo)
                icone = ICONES_FIXOS.get(rotulo.lower())
                if icone is None:
                    pixmap = _carregar_pixmap_icone(self._icones_steam.get(rotulo.lower()))
                    if pixmap is not None:
                        icone = pixmap
                    else:
                        icone = ICONE_PADRAO if categoria_pai is None else "•"
        # Ícone customizado sempre GANHA de qualquer resolução padrão acima
        # (fixo, real da Steam, ou de categoria), mas só muda a EXIBIÇÃO - a
        # identidade real (`rotulo`) continua intacta.
        icone_customizado = radial_menu.obter_icone_customizado(rotulo)
        if icone_customizado:
            if radial_menu.eh_caminho_icone_customizado(icone_customizado):
                pixmap_customizado = _carregar_pixmap_icone(icone_customizado)
                if pixmap_customizado is not None:
                    icone = pixmap_customizado
                # arquivo sumiu/corrompeu - fica com o ícone padrão já resolvido acima
            else:
                icone = icone_customizado
        apelido = radial_menu.obter_apelido(rotulo)
        if apelido:
            texto = apelido
        return icone, texto

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        cx = cy = self.tamanho_atual / 2

        for indice_nivel in range(len(self.pilha), 0, -1):
            nivel = self.pilha[indice_nivel - 1]
            favoritavel = _categoria_favoritavel(nivel["categoria"])
            proxima = self.pilha[indice_nivel]["categoria"] if len(self.pilha) > indice_nivel else None
            referencia_nivel = self._referencia_nivel(indice_nivel, len(nivel["exibidos"]))
            self._desenhar_anel(
                painter, nivel["exibidos"], _capacidade_nivel(indice_nivel),
                _raio_interno_nivel(indice_nivel), _raio_externo_nivel(indice_nivel),
                nivel["hover"], f"n{indice_nivel}",
                lambda r, cp=nivel["categoria"]: self._resolver_item(r, cp),
                todos_coloridos=False, mostrar_indicador_favorito=favoritavel, proxima_categoria=proxima,
                referencia=referencia_nivel,
            )

        proxima_de_favoritos = self.pilha[0]["categoria"] if self.pilha else None
        self._desenhar_anel(
            painter, self.rotulos, _capacidade_nivel(0), RAIO_INTERNO, RAIO_EXTERNO_1, self.indice_hover, "n0",
            lambda r: self._resolver_item(r, None),
            todos_coloridos=False, proxima_categoria=proxima_de_favoritos,
        )

        gradiente_centro = QRadialGradient(cx, cy, RAIO_INTERNO)
        gradiente_centro.setColorAt(0.0, QColor(26, 26, 29, 245))
        gradiente_centro.setColorAt(1.0, QColor(16, 16, 18, 245))
        painter.setBrush(QBrush(gradiente_centro))
        painter.setPen(QPen(QColor("#2f2f34"), 2))
        painter.drawEllipse(QRectF(cx - RAIO_INTERNO, cy - RAIO_INTERNO, RAIO_INTERNO * 2, RAIO_INTERNO * 2))

        cpu = self.metricas.get("cpu_percent")
        if cpu is not None:
            pen_anel = QPen(QColor("#a855f7"), 5)
            pen_anel.setCapStyle(Qt.RoundCap)
            painter.setPen(pen_anel)
            painter.setBrush(Qt.NoBrush)
            raio_anel = RAIO_INTERNO - 8
            rect_anel = QRectF(cx - raio_anel, cy - raio_anel, raio_anel * 2, raio_anel * 2)
            painter.drawArc(rect_anel, 90 * 16, -int(cpu / 100 * 360 * 16))

        # Indicador de página - minimalista, dentro do círculo central em vez
        # de um texto grande na borda inferior; mostra só os anéis que estão
        # de fato paginados agora (favoritos + qualquer nível aberto).
        partes_pagina = []
        if self.total_paginas_1 > 1:
            partes_pagina.append(f"{self.pagina_1 + 1}/{self.total_paginas_1}")
        for nivel in self.pilha:
            if nivel["total_paginas"] > 1:
                partes_pagina.append(f"{nivel['pagina'] + 1}/{nivel['total_paginas']}")
        if partes_pagina:
            painter.setPen(QColor("#8f8d8a"))
            painter.setFont(QFont("Segoe UI", 8, QFont.Bold))
            painter.drawText(QRectF(cx - RAIO_INTERNO, cy - 50, RAIO_INTERNO * 2, 14), Qt.AlignCenter, " · ".join(partes_pagina))

        painter.setPen(QColor("#f1efe9"))
        painter.setFont(QFont("Segoe UI", 16, QFont.Bold))
        painter.drawText(QRectF(cx - RAIO_INTERNO, cy - 32, RAIO_INTERNO * 2, 26), Qt.AlignCenter, datetime.now().strftime("%H:%M"))

        painter.setPen(QColor("#8f8d8a"))
        painter.setFont(QFont("Segoe UI", 8))
        agora_data = datetime.now()
        texto_data = f"{DIAS_SEMANA_ABREV[agora_data.weekday()]}, {agora_data.day:02d} {MESES_ABREV[agora_data.month - 1]}".upper()
        painter.drawText(QRectF(cx - RAIO_INTERNO, cy - 8, RAIO_INTERNO * 2, 16), Qt.AlignCenter, texto_data)

        if cpu is not None:
            texto_hw = f"CPU {cpu:.0f}%"
            ram = self.metricas.get("ram_percent")
            if ram is not None:
                texto_hw += f"  RAM {ram:.0f}%"
            gpu = self.metricas.get("gpu_percent")
            if gpu is not None:
                texto_hw += f"  GPU {gpu:.0f}%"
        else:
            texto_hw = "Carregando..."
        painter.setPen(QColor("#8f8d8a"))
        painter.setFont(QFont("Segoe UI", 8))
        painter.drawText(QRectF(cx - RAIO_INTERNO, cy + 12, RAIO_INTERNO * 2, 30), Qt.AlignCenter | Qt.TextWordWrap, texto_hw)

        # Busca rápida - overlay simples na margem superior, complementa a
        # navegação por clique sem substituí-la.
        if self.filtro_busca:
            painter.setPen(QColor("#f1efe9"))
            painter.setFont(QFont("Segoe UI", 11, QFont.Bold))
            painter.drawText(QRectF(0, 6, self.tamanho_atual, 24), Qt.AlignCenter, f"🔎 {self.filtro_busca}")

        painter.end()


_popup_atual = None


def mostrar_menu_radial_qt():
    """Ponto de entrada público - chamado pelo hotkey global (Ctrl+Alt+Espaço,
    ver `iris/main.py`). 2º toque fecha o popup (toggle). Precisa rodar na GUI
    thread (Qt) - `main.py` marshalla a chamada do hook de teclado pra lá
    antes de chamar isto."""
    global _popup_atual
    if _popup_atual is not None:
        try:
            _popup_atual.close()
        except Exception:
            pass
        _popup_atual = None
        return

    if not radial_menu.obter_favoritos():
        print(" [SISTEMA] Menu Radial: nenhum favorito configurado ainda - abra Configurações pra escolher.")
        return

    janela = RadialMenuQt()
    _popup_atual = janela
    janela.show()
    janela.raise_()
    janela.activateWindow()
    janela.setFocus()
    # O DWM do Windows às vezes só compõe parcialmente o 1º frame de uma
    # janela translúcida (WA_TranslucentBackground) quando ela abre
    # SOBREPONDO outra janela do mesmo app (ex.: a tela de Configurações
    # visível e em foco) - sobra só 1 fatia "fantasma" desenhada até o
    # DWM recompor de verdade. Um `repaint()` sozinho não bastou (é um
    # repaint do lado do Qt, não força o DWM a recompor a SUPERFÍCIE da
    # janela) - um "nudge" de geometria de verdade (redimensionar e voltar)
    # força o Windows a recriar a superfície da janela do zero.
    def _forcar_recomposicao_dwm():
        if janela is None or not janela.isVisible():
            return
        # move() (não resize()) de propósito - o popup usa setFixedSize, que
        # ignoraria um resize "nudge" (largura/altura ficam presas ao
        # mínimo/máximo fixado).
        pos = janela.pos()
        janela.move(pos.x() + 1, pos.y())
        janela.move(pos)
        janela.repaint()

    QTimer.singleShot(0, _forcar_recomposicao_dwm)
    QTimer.singleShot(60, _forcar_recomposicao_dwm)
