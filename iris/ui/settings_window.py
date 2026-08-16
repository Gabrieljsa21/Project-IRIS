# -*- coding: utf-8 -*-
"""Tela de Configurações do IRIS - único jeito de gerenciar favoritos,
categorias, pastas e jogos da Steam quando rodando standalone (sem a GAIA,
não existe nenhum outro Painel gráfico apontando pra este `data/
menu_radial_config.json`). Não tenta reproduzir cada detalhe da tela
equivalente da GAIA (`ui/qt_modais/menu_radial.py`, não portada - fora do
escopo desta extração) - só o necessário pra configurar o launcher sozinho:
favoritos, categorias, pastas, Steam e as poucas preferências do core."""
import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFileDialog, QHBoxLayout, QVBoxLayout, QWidget

import iris.core.app_launcher as app_launcher_mod
import iris.core.radial_menu as radial_menu
from iris.plugins import registry as plugin_registry
from iris.ui.qt_widgets import (
    GAIA_GOLD, TEXT_COLOR,
    ModalBase, Switch, criar_botao, criar_botao_pequeno, criar_checkbox,
    criar_descricao, criar_dropdown, criar_frame_item, criar_lineedit,
    criar_scroll_area, criar_spinbox, criar_tabwidget, criar_titulo_secao,
    avisar, confirmar_acao, executar_em_thread,
)


class JanelaConfiguracoes(ModalBase):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("IRIS - Configurações")
        self.resize(720, 560)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        abas = criar_tabwidget()
        layout.addWidget(abas)

        abas.addTab(self._construir_aba_favoritos(), "Favoritos")
        abas.addTab(self._construir_aba_categorias(), "Categorias")
        abas.addTab(self._construir_aba_pastas(), "Pastas")
        abas.addTab(self._construir_aba_steam(), "Steam")
        abas.addTab(self._construir_aba_preferencias(), "Preferências")

    # ------------------------------------------------------------------
    # Favoritos
    # ------------------------------------------------------------------
    def _construir_aba_favoritos(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.addWidget(criar_descricao(
            "Ordem de exibição no anel de favoritos do popup. Categorias "
            "(próprias ou de um plugin disponível agora) também podem ser "
            "favoritadas - abrem um submenu em vez de lançar algo direto."
        ))

        self._scroll_favoritos, self._layout_favoritos = criar_scroll_area()
        layout.addWidget(self._scroll_favoritos, stretch=1)

        linha_add = QHBoxLayout()
        self._dropdown_add_favorito = criar_dropdown(self._itens_disponiveis_para_favoritar())
        linha_add.addWidget(self._dropdown_add_favorito, stretch=1)
        botao_add = criar_botao("Adicionar aos favoritos", preenchido=True)
        botao_add.clicked.connect(self._adicionar_favorito)
        linha_add.addWidget(botao_add)
        layout.addLayout(linha_add)

        self._atualizar_lista_favoritos()
        return widget

    def _itens_disponiveis_para_favoritar(self):
        favoritos_atuais = set(radial_menu.obter_favoritos())
        apps = app_launcher_mod.listar_nomes_apps_disponiveis()
        especiais = list(radial_menu.ITENS_ESPECIAIS)
        categorias = list(radial_menu.obter_categorias().keys())
        plugins = [p.rotulo_categoria for p in plugin_registry.providers_disponiveis()]
        todos = especiais + plugins + categorias + apps
        return [item for item in todos if item not in favoritos_atuais]

    def _atualizar_lista_favoritos(self):
        while self._layout_favoritos.count():
            item = self._layout_favoritos.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        favoritos = radial_menu.obter_favoritos()
        desativados = radial_menu.obter_favoritos_desativados()
        for indice, rotulo in enumerate(favoritos):
            frame = criar_frame_item()
            linha = QHBoxLayout(frame)
            linha.setContentsMargins(10, 6, 10, 6)

            switch = Switch("Ativo", "Inativo", marcado=rotulo not in desativados)
            switch.stateChanged.connect(lambda _estado, r=rotulo, s=switch: self._alternar_favorito_ativo(r, s.isChecked()))
            linha.addWidget(switch)

            linha.addWidget(_LabelSimples(rotulo), stretch=1)

            botao_cima = criar_botao_pequeno("↑", TEXT_COLOR)
            botao_cima.setEnabled(indice > 0)
            botao_cima.clicked.connect(lambda _c=False, i=indice: self._mover_favorito(i, -1))
            linha.addWidget(botao_cima)

            botao_baixo = criar_botao_pequeno("↓", TEXT_COLOR)
            botao_baixo.setEnabled(indice < len(favoritos) - 1)
            botao_baixo.clicked.connect(lambda _c=False, i=indice: self._mover_favorito(i, 1))
            linha.addWidget(botao_baixo)

            botao_remover = criar_botao_pequeno("✕", "#f38ba8")
            botao_remover.clicked.connect(lambda _c=False, r=rotulo: self._remover_favorito(r))
            linha.addWidget(botao_remover)

            self._layout_favoritos.addWidget(frame)

    def _adicionar_favorito(self):
        rotulo = self._dropdown_add_favorito.currentText()
        if not rotulo:
            return
        favoritos = radial_menu.obter_favoritos()
        if rotulo in favoritos:
            return
        radial_menu.salvar_favoritos(favoritos + [rotulo])
        self._atualizar_lista_favoritos()
        novo_valor_dropdown = self._itens_disponiveis_para_favoritar()
        self._dropdown_add_favorito.clear()
        self._dropdown_add_favorito.addItems(novo_valor_dropdown)

    def _remover_favorito(self, rotulo):
        favoritos = [f for f in radial_menu.obter_favoritos() if f != rotulo]
        radial_menu.salvar_favoritos(favoritos)
        self._atualizar_lista_favoritos()
        self._dropdown_add_favorito.addItem(rotulo)

    def _mover_favorito(self, indice, direcao):
        favoritos = radial_menu.obter_favoritos()
        novo_indice = indice + direcao
        if not (0 <= novo_indice < len(favoritos)):
            return
        favoritos[indice], favoritos[novo_indice] = favoritos[novo_indice], favoritos[indice]
        radial_menu.salvar_favoritos(favoritos)
        self._atualizar_lista_favoritos()

    def _alternar_favorito_ativo(self, rotulo, ativo):
        radial_menu.definir_favorito_ativo(rotulo, ativo)

    # ------------------------------------------------------------------
    # Categorias
    # ------------------------------------------------------------------
    def _construir_aba_categorias(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.addWidget(criar_descricao(
            "Categoria própria com uma lista de apps/pastas/outras categorias "
            "dentro. Selecionar uma categoria já existente carrega ela pra "
            "edição - salvar de novo sobrescreve os itens."
        ))

        self._scroll_categorias, self._layout_categorias = criar_scroll_area()
        layout.addWidget(self._scroll_categorias, stretch=1)

        layout.addWidget(criar_titulo_secao("Criar / editar categoria", tamanho=12))
        linha_nome = QHBoxLayout()
        self._campo_nome_categoria = criar_lineedit()
        self._campo_nome_categoria.setPlaceholderText("Nome da categoria")
        linha_nome.addWidget(self._campo_nome_categoria, stretch=2)
        self._campo_icone_categoria = criar_lineedit("📁")
        self._campo_icone_categoria.setFixedWidth(60)
        linha_nome.addWidget(self._campo_icone_categoria)
        layout.addLayout(linha_nome)

        self._scroll_itens_categoria, self._layout_itens_categoria = criar_scroll_area()
        self._scroll_itens_categoria.setFixedHeight(140)
        self._checkboxes_itens_categoria = {}
        self._preencher_checkboxes_itens_categoria()
        layout.addWidget(self._scroll_itens_categoria)

        botao_salvar = criar_botao("Salvar categoria", preenchido=True)
        botao_salvar.clicked.connect(self._salvar_categoria)
        layout.addWidget(botao_salvar)

        self._atualizar_lista_categorias()
        return widget

    def _preencher_checkboxes_itens_categoria(self, itens_marcados=None):
        itens_marcados = itens_marcados or []
        while self._layout_itens_categoria.count():
            item = self._layout_itens_categoria.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._checkboxes_itens_categoria = {}

        apps = app_launcher_mod.listar_nomes_apps_disponiveis()
        for nome in apps:
            caixa = criar_checkbox(nome, marcado=nome in itens_marcados)
            self._checkboxes_itens_categoria[nome] = caixa
            self._layout_itens_categoria.addWidget(caixa)

    def _atualizar_lista_categorias(self):
        while self._layout_categorias.count():
            item = self._layout_categorias.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for nome, dados in radial_menu.obter_categorias().items():
            frame = criar_frame_item()
            linha = QHBoxLayout(frame)
            linha.setContentsMargins(10, 6, 10, 6)

            switch = Switch("Ativa", "Inativa", marcado=dados.get("ativa", True))
            switch.stateChanged.connect(lambda _e, n=nome, s=switch: radial_menu.definir_categoria_ativa(n, s.isChecked()))
            linha.addWidget(switch)

            texto = f"{dados.get('icone', '📁')} {nome} ({len(dados.get('itens', []))} itens)"
            linha.addWidget(_LabelSimples(texto), stretch=1)

            botao_editar = criar_botao_pequeno("✎", GAIA_GOLD)
            botao_editar.clicked.connect(lambda _c=False, n=nome: self._carregar_categoria_para_edicao(n))
            linha.addWidget(botao_editar)

            botao_remover = criar_botao_pequeno("✕", "#f38ba8")
            botao_remover.clicked.connect(lambda _c=False, n=nome: self._remover_categoria(n))
            linha.addWidget(botao_remover)

            self._layout_categorias.addWidget(frame)

    def _carregar_categoria_para_edicao(self, nome):
        dados = radial_menu.obter_categorias().get(nome, {})
        self._campo_nome_categoria.setText(nome)
        self._campo_icone_categoria.setText(dados.get("icone", "📁"))
        self._preencher_checkboxes_itens_categoria(dados.get("itens", []))

    def _salvar_categoria(self):
        nome = self._campo_nome_categoria.text().strip()
        if not nome:
            avisar(self, "Categoria sem nome", "Escolha um nome pra categoria antes de salvar.")
            return
        icone = self._campo_icone_categoria.text().strip() or "📁"
        itens = [nome_item for nome_item, caixa in self._checkboxes_itens_categoria.items() if caixa.isChecked()]
        radial_menu.salvar_categoria(nome, itens, icone=icone)
        self._atualizar_lista_categorias()
        self._dropdown_add_favorito.addItem(nome) if nome not in radial_menu.obter_favoritos() else None

    def _remover_categoria(self, nome):
        if not confirmar_acao(self, "Remover categoria", f"Remover a categoria '{nome}'?"):
            return
        radial_menu.remover_categoria(nome)
        favoritos = [f for f in radial_menu.obter_favoritos() if f != nome]
        radial_menu.salvar_favoritos(favoritos)
        self._atualizar_lista_categorias()
        self._atualizar_lista_favoritos()

    # ------------------------------------------------------------------
    # Pastas
    # ------------------------------------------------------------------
    def _construir_aba_pastas(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.addWidget(criar_descricao("Pastas que aparecem dentro da categoria \"📂 Pastas\"."))

        self._scroll_pastas, self._layout_pastas = criar_scroll_area()
        layout.addWidget(self._scroll_pastas, stretch=1)

        linha_add = QHBoxLayout()
        self._campo_nome_pasta = criar_lineedit()
        self._campo_nome_pasta.setPlaceholderText("Nome exibido")
        linha_add.addWidget(self._campo_nome_pasta, stretch=1)
        self._campo_caminho_pasta = criar_lineedit()
        self._campo_caminho_pasta.setPlaceholderText("C:/caminho/completo")
        linha_add.addWidget(self._campo_caminho_pasta, stretch=2)
        botao_escolher = criar_botao("Escolher...")
        botao_escolher.clicked.connect(self._escolher_pasta)
        linha_add.addWidget(botao_escolher)
        botao_add = criar_botao("Adicionar", preenchido=True)
        botao_add.clicked.connect(self._adicionar_pasta)
        linha_add.addWidget(botao_add)
        layout.addLayout(linha_add)

        self._atualizar_lista_pastas()
        return widget

    def _escolher_pasta(self):
        caminho = QFileDialog.getExistingDirectory(self, "Escolher pasta")
        if caminho:
            self._campo_caminho_pasta.setText(caminho)

    def _adicionar_pasta(self):
        nome = self._campo_nome_pasta.text().strip()
        caminho = self._campo_caminho_pasta.text().strip()
        if not nome or not caminho:
            avisar(self, "Pasta incompleta", "Preencha o nome e o caminho da pasta.")
            return
        if not os.path.isdir(caminho):
            avisar(self, "Caminho inválido", "Esse caminho não é uma pasta válida neste PC.")
            return
        radial_menu.adicionar_pasta(nome, caminho)
        self._campo_nome_pasta.clear()
        self._campo_caminho_pasta.clear()
        self._atualizar_lista_pastas()

    def _atualizar_lista_pastas(self):
        while self._layout_pastas.count():
            item = self._layout_pastas.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for nome, info in radial_menu.obter_pastas_todas().items():
            frame = criar_frame_item()
            linha = QHBoxLayout(frame)
            linha.setContentsMargins(10, 6, 10, 6)

            switch = Switch("Ativa", "Inativa", marcado=info.get("ativa", True))
            switch.stateChanged.connect(lambda _e, n=nome, s=switch: radial_menu.definir_pasta_ativa(n, s.isChecked()))
            linha.addWidget(switch)

            linha.addWidget(_LabelSimples(f"{nome}  -  {info.get('caminho', '')}"), stretch=1)

            botao_remover = criar_botao_pequeno("✕", "#f38ba8")
            botao_remover.clicked.connect(lambda _c=False, n=nome: self._remover_pasta(n))
            linha.addWidget(botao_remover)

            self._layout_pastas.addWidget(frame)

    def _remover_pasta(self, nome):
        radial_menu.remover_pasta(nome)
        self._atualizar_lista_pastas()

    # ------------------------------------------------------------------
    # Steam
    # ------------------------------------------------------------------
    def _construir_aba_steam(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.addWidget(criar_descricao(
            "Jogos da Steam instalados agora (categoria \"🎮 Steam\" do popup). "
            "Reescanear atualiza a lista sem precisar reiniciar o IRIS."
        ))

        self._scroll_steam, self._layout_steam = criar_scroll_area()
        layout.addWidget(self._scroll_steam, stretch=1)

        botao_reescanear = criar_botao("Reescanear apps (Steam + Menu Iniciar)", preenchido=True)
        botao_reescanear.clicked.connect(self._reescanear_apps)
        layout.addWidget(botao_reescanear)

        self._atualizar_lista_steam()
        return widget

    def _jogos_steam_ordenados(self):
        instalados = app_launcher_mod.listar_jogos_steam_instalados()
        return radial_menu.mesclar_ordem_steam(instalados)

    def _atualizar_lista_steam(self):
        while self._layout_steam.count():
            item = self._layout_steam.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        jogos = self._jogos_steam_ordenados()
        desativados = radial_menu.obter_steam_desativados()
        if not jogos:
            self._layout_steam.addWidget(criar_descricao("Nenhum jogo da Steam encontrado ainda - clique em Reescanear."))
            return

        for indice, nome in enumerate(jogos):
            frame = criar_frame_item()
            linha = QHBoxLayout(frame)
            linha.setContentsMargins(10, 6, 10, 6)

            switch = Switch("Ativo", "Inativo", marcado=nome not in desativados)
            switch.stateChanged.connect(lambda _e, n=nome, s=switch: radial_menu.definir_steam_jogo_ativo(n, s.isChecked()))
            linha.addWidget(switch)

            linha.addWidget(_LabelSimples(nome.title()), stretch=1)

            botao_cima = criar_botao_pequeno("↑", TEXT_COLOR)
            botao_cima.setEnabled(indice > 0)
            botao_cima.clicked.connect(lambda _c=False, i=indice: self._mover_steam(i, -1))
            linha.addWidget(botao_cima)

            botao_baixo = criar_botao_pequeno("↓", TEXT_COLOR)
            botao_baixo.setEnabled(indice < len(jogos) - 1)
            botao_baixo.clicked.connect(lambda _c=False, i=indice: self._mover_steam(i, 1))
            linha.addWidget(botao_baixo)

            self._layout_steam.addWidget(frame)

    def _mover_steam(self, indice, direcao):
        jogos = self._jogos_steam_ordenados()
        novo_indice = indice + direcao
        if not (0 <= novo_indice < len(jogos)):
            return
        jogos[indice], jogos[novo_indice] = jogos[novo_indice], jogos[indice]
        radial_menu.salvar_steam_ordem(jogos)
        self._atualizar_lista_steam()

    def _reescanear_apps(self):
        def _trabalho():
            return app_launcher_mod.AppLauncher().escanear_apps()

        def _ao_terminar(resultado, erro):
            if erro:
                avisar(self, "Erro ao escanear", str(erro))
                return
            self._atualizar_lista_steam()
            avisar(self, "Escaneamento concluído", resultado)

        executar_em_thread(_trabalho, _ao_terminar, parent=self)

    # ------------------------------------------------------------------
    # Preferências
    # ------------------------------------------------------------------
    def _construir_aba_preferencias(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignTop)
        layout.setSpacing(14)

        switch_ranking = Switch("Ranking automático ligado", "Ranking automático desligado",
                                 marcado=radial_menu.obter_ranking_automatico_ativo())
        switch_ranking.stateChanged.connect(lambda _e, s=switch_ranking: radial_menu.salvar_ranking_automatico_ativo(s.isChecked()))
        layout.addWidget(switch_ranking)
        layout.addWidget(criar_descricao("Reordena os favoritos por frequência de uso automaticamente toda vez que o popup fecha."))

        botao_ordenar = criar_botao("Ordenar favoritos por mais usados agora")
        botao_ordenar.clicked.connect(lambda: (radial_menu.ordenar_favoritos_por_uso(), self._atualizar_lista_favoritos()))
        layout.addWidget(botao_ordenar)

        linha_limite_fav = QHBoxLayout()
        linha_limite_fav.addWidget(_LabelSimples("Limite de itens no anel de favoritos:"))
        spin_fav = criar_spinbox(3, 24, radial_menu.obter_limite_por_camada_favoritos())
        spin_fav.valueChanged.connect(radial_menu.salvar_limite_por_camada_favoritos)
        linha_limite_fav.addWidget(spin_fav)
        linha_limite_fav.addStretch(1)
        layout.addLayout(linha_limite_fav)

        linha_limite_sub = QHBoxLayout()
        linha_limite_sub.addWidget(_LabelSimples("Limite de itens em cada anel de categoria:"))
        spin_sub = criar_spinbox(3, 24, radial_menu.obter_limite_por_camada_subitens())
        spin_sub.valueChanged.connect(radial_menu.salvar_limite_por_camada_subitens)
        linha_limite_sub.addWidget(spin_sub)
        linha_limite_sub.addStretch(1)
        layout.addLayout(linha_limite_sub)

        layout.addWidget(criar_titulo_secao("Plugins", tamanho=12))
        registrados = plugin_registry.providers_registrados()
        if not registrados:
            layout.addWidget(criar_descricao("Nenhum plugin instalado neste processo."))
        else:
            for provider in registrados:
                disponivel = provider.esta_disponivel()
                status = "disponível agora" if disponivel else "instalado, indisponível agora"
                layout.addWidget(criar_descricao(f"• {provider.rotulo_categoria}  ({provider.id})  -  {status}"))

        layout.addStretch(1)
        return widget


class _LabelSimples(QWidget):
    """QLabel com fundo/borda explicitamente transparentes (QLabel herda de
    QFrame - sem isso ele herda o estilo do container pai, ex.: a borda de um
    `criar_frame_item`)."""

    def __init__(self, texto, parent=None):
        super().__init__(parent)
        from PySide6.QtWidgets import QLabel
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        lbl = QLabel(texto)
        lbl.setStyleSheet(f"color: {TEXT_COLOR}; background: transparent; border: none;")
        lbl.setWordWrap(True)
        layout.addWidget(lbl)
