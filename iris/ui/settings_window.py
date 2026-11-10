# -*- coding: utf-8 -*-
"""Tela de Configurações do IRIS - único jeito de gerenciar favoritos,
categorias, pastas e jogos da Steam quando rodando standalone (sem a GAIA,
não existe nenhum outro Painel gráfico apontando pra este `data/
menu_radial_config.json`). Não tenta reproduzir cada detalhe da tela
equivalente da GAIA (`ui/qt_modais/menu_radial.py`, não portada - fora do
escopo desta extração) - só o necessário pra configurar o launcher sozinho:
favoritos, categorias, pastas, Steam e as poucas preferências do core."""
import json
import os
import subprocess

from PySide6.QtWidgets import QFileDialog, QHBoxLayout, QVBoxLayout, QWidget

import iris.core.app_launcher as app_launcher_mod
import iris.core.radial_menu as radial_menu
from iris.core import armazenamento
from iris.core.atalho import descrever_atalho
from iris.plugins import registry as plugin_registry
from iris.ui.qt_widgets import (
    GAIA_GOLD, TEXT_COLOR,
    ModalBase, Switch, criar_botao, criar_botao_pequeno, criar_checkbox,
    criar_descricao, criar_dropdown, criar_frame_item, criar_lineedit,
    criar_scroll_area, criar_spinbox, criar_tabwidget, criar_titulo_secao,
    avisar, confirmar_acao, executar_em_thread,
)


class JanelaConfiguracoes(ModalBase):
    def __init__(self, parent=None, ao_mudar_atalho=None, atalho_em_uso=None):
        """`ao_mudar_atalho(texto) -> (ok, mensagem)` registra o atalho novo
        na hora (`iris/main.py::IrisApp.aplicar_atalho`); `atalho_em_uso()`
        devolve o que está registrado agora. Sem eles (janela aberta fora do
        app, em teste), o campo só salva pra valer no próximo início."""
        super().__init__(parent)
        self.setWindowTitle("IRIS - Configurações")
        self.resize(720, 560)
        self._editando_categoria = None
        self._ao_mudar_atalho = ao_mudar_atalho
        self._atalho_em_uso = atalho_em_uso

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        abas = criar_tabwidget()
        layout.addWidget(abas)

        abas.addTab(self._construir_aba_favoritos(), "Favoritos")
        abas.addTab(self._construir_aba_categorias(), "Categorias")
        abas.addTab(self._construir_aba_pastas(), "Pastas")
        abas.addTab(self._construir_aba_steam(), "Steam")
        abas.addTab(self._construir_aba_personalizar(), "Personalizar")
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
        """Apps + pastas + OUTRAS categorias como itens selecionáveis - a
        categoria sendo editada agora (`self._editando_categoria`) fica de
        fora (não dá pra colocar uma categoria dentro dela mesma). Ciclos
        INDIRETOS (A contém B, B contém A) não são bloqueados aqui - o
        próprio popup já protege contra isso em runtime
        (`_cadeia_categorias_atual`, `iris/ui/menu_radial_qt.py`)."""
        itens_marcados = itens_marcados or []
        while self._layout_itens_categoria.count():
            item = self._layout_itens_categoria.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._checkboxes_itens_categoria = {}

        apps = app_launcher_mod.listar_nomes_apps_disponiveis()
        pastas = [f"📁 {nome}" for nome in radial_menu.obter_pastas().keys()]
        outras_categorias = [
            nome for nome in radial_menu.obter_categorias().keys()
            if nome != self._editando_categoria
        ]
        for nome in apps + pastas + outras_categorias:
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
        self._editando_categoria = nome
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
        self._editando_categoria = None
        self._campo_nome_categoria.clear()
        self._campo_icone_categoria.setText("📁")
        self._preencher_checkboxes_itens_categoria()

    def _remover_categoria(self, nome):
        if not confirmar_acao(self, "Remover categoria", f"Remover a categoria '{nome}'?"):
            return
        radial_menu.remover_categoria(nome)
        favoritos = [f for f in radial_menu.obter_favoritos() if f != nome]
        radial_menu.salvar_favoritos(favoritos)
        self._atualizar_lista_categorias()
        self._atualizar_lista_favoritos()
        if self._editando_categoria == nome:
            self._editando_categoria = None
            self._campo_nome_categoria.clear()
            self._campo_icone_categoria.setText("📁")
        self._preencher_checkboxes_itens_categoria()

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

        botao_importar = criar_botao("Importar de outro menu_radial_config.json...")
        botao_importar.clicked.connect(self._importar_pastas_de_arquivo)
        layout.addWidget(botao_importar)
        layout.addWidget(criar_descricao("Lê a chave \"pastas\" de um config compatível (ex.: o do Menu Radial da GAIA) e importa as que existirem neste PC."))

        self._atualizar_lista_pastas()
        return widget

    def _importar_pastas_de_arquivo(self):
        caminho_arquivo, _ = QFileDialog.getOpenFileName(
            self, "Importar pastas de um menu_radial_config.json", "", "JSON (*.json)"
        )
        if not caminho_arquivo:
            return
        try:
            with open(caminho_arquivo, "r", encoding="utf-8") as f:
                dados = json.load(f)
        except Exception as e:
            avisar(self, "Erro ao ler arquivo", str(e))
            return
        pastas = dados.get("pastas", {})
        if not isinstance(pastas, dict) or not pastas:
            avisar(self, "Nada pra importar", "Esse arquivo não tem nenhuma pasta configurada (chave \"pastas\").")
            return
        validas = {nome: info for nome, info in pastas.items()
                   if isinstance(info, dict) and os.path.isdir(info.get("caminho", ""))}
        ignoradas = len(pastas) - len(validas)
        if not validas:
            avisar(self, "Nenhuma pasta válida", "Nenhum dos caminhos encontrados existe neste PC.")
            return
        total = radial_menu.importar_pastas(validas)
        self._atualizar_lista_pastas()
        mensagem = f"{total} pasta(s) importada(s)."
        if ignoradas:
            mensagem += f" {ignoradas} ignorada(s) por não existir(em) neste PC."
        avisar(self, "Importação concluída", mensagem)

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
    # Personalizar - apelido (texto exibido) e ícone de qualquer item, sem
    # mudar a identidade usada pra abrir. Mesmo desenho da aba Categorias:
    # lista do que existe em cima, formulário de criar/editar embaixo.
    # ------------------------------------------------------------------
    def _construir_aba_personalizar(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.addWidget(criar_descricao(
            "Troca o nome exibido e/ou o ícone de um item do menu. O item "
            "continua abrindo a mesma coisa; muda só a aparência."
        ))

        self._scroll_personalizacoes, self._layout_personalizacoes = criar_scroll_area()
        layout.addWidget(self._scroll_personalizacoes, stretch=1)

        layout.addWidget(criar_titulo_secao("Personalizar um item", tamanho=12))
        self._dropdown_item_personalizar = criar_dropdown(self._itens_personalizaveis())
        self._dropdown_item_personalizar.currentTextChanged.connect(self._carregar_personalizacao)
        layout.addWidget(self._dropdown_item_personalizar)

        linha = QHBoxLayout()
        self._campo_apelido = criar_lineedit()
        self._campo_apelido.setPlaceholderText("Nome exibido (vazio = nome original)")
        linha.addWidget(self._campo_apelido, stretch=2)
        self._campo_icone_item = criar_lineedit()
        self._campo_icone_item.setPlaceholderText("Emoji ou imagem")
        linha.addWidget(self._campo_icone_item, stretch=1)
        botao_imagem = criar_botao("Imagem...")
        botao_imagem.clicked.connect(self._escolher_imagem_icone)
        linha.addWidget(botao_imagem)
        botao_salvar = criar_botao("Salvar", preenchido=True)
        botao_salvar.clicked.connect(self._salvar_personalizacao)
        linha.addWidget(botao_salvar)
        layout.addLayout(linha)

        self._imagem_icone_escolhida = None
        self._atualizar_lista_personalizacoes()
        self._carregar_personalizacao(self._dropdown_item_personalizar.currentText())
        return widget

    def _itens_personalizaveis(self):
        """Tudo que pode aparecer numa fatia: favoritos, itens especiais,
        categorias e o que há dentro delas, pastas, apps - sem repetir, na
        ordem em que o usuário mais provavelmente procura (o que já está no
        menu primeiro)."""
        categorias = radial_menu.obter_categorias()
        vistos, itens = set(), []
        grupos = [
            radial_menu.obter_favoritos(),
            list(radial_menu.obter_personalizacoes().keys()),
            list(categorias.keys()),
            [i for dados in categorias.values() for i in dados.get("itens", [])],
            [f"📁 {nome}" for nome in radial_menu.obter_pastas_todas().keys()],
            list(radial_menu.ITENS_ESPECIAIS),
            [p.rotulo_categoria for p in plugin_registry.providers_registrados()],
            app_launcher_mod.listar_nomes_apps_disponiveis(),
        ]
        for grupo in grupos:
            for item in grupo:
                if item not in vistos:
                    vistos.add(item)
                    itens.append(item)
        return itens

    def _atualizar_lista_personalizacoes(self):
        while self._layout_personalizacoes.count():
            item = self._layout_personalizacoes.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        personalizacoes = radial_menu.obter_personalizacoes()
        if not personalizacoes:
            self._layout_personalizacoes.addWidget(criar_descricao("Nenhum item personalizado ainda."))
            return
        for item_real, dados in personalizacoes.items():
            frame = criar_frame_item()
            linha = QHBoxLayout(frame)
            linha.setContentsMargins(10, 6, 10, 6)

            partes = []
            if dados.get("apelido"):
                partes.append(f"nome: {dados['apelido']}")
            icone = dados.get("icone")
            if icone:
                eh_imagem = radial_menu.eh_caminho_icone_customizado(icone)
                partes.append("ícone: imagem própria" if eh_imagem else f"ícone: {icone}")
            linha.addWidget(_LabelSimples(f"{item_real}  -  {', '.join(partes)}"), stretch=1)

            botao_editar = criar_botao_pequeno("✎", GAIA_GOLD)
            botao_editar.clicked.connect(lambda _c=False, i=item_real: self._editar_personalizacao(i))
            linha.addWidget(botao_editar)

            botao_remover = criar_botao_pequeno("✕", "#f38ba8")
            botao_remover.clicked.connect(lambda _c=False, i=item_real: self._remover_personalizacao(i))
            linha.addWidget(botao_remover)

            self._layout_personalizacoes.addWidget(frame)

    def _editar_personalizacao(self, item_real):
        if self._dropdown_item_personalizar.findText(item_real) < 0:
            self._dropdown_item_personalizar.addItem(item_real)
        self._dropdown_item_personalizar.setCurrentText(item_real)
        self._carregar_personalizacao(item_real)

    def _carregar_personalizacao(self, item_real):
        dados = radial_menu.obter_personalizacoes().get(item_real, {})
        self._imagem_icone_escolhida = None
        self._campo_apelido.setText(dados.get("apelido", ""))
        icone = dados.get("icone", "")
        if radial_menu.eh_caminho_icone_customizado(icone):
            self._campo_icone_item.setText("")
            self._campo_icone_item.setPlaceholderText("imagem própria (mantida)")
        else:
            self._campo_icone_item.setText(icone)
            self._campo_icone_item.setPlaceholderText("Emoji ou imagem")

    def _escolher_imagem_icone(self):
        extensoes = " ".join(f"*{e}" for e in radial_menu.EXTENSOES_ICONE_VALIDAS)
        caminho, _ = QFileDialog.getOpenFileName(self, "Escolher imagem do ícone", "", f"Imagens ({extensoes})")
        if caminho:
            self._imagem_icone_escolhida = caminho
            self._campo_icone_item.setText("")
            self._campo_icone_item.setPlaceholderText(os.path.basename(caminho))

    def _salvar_personalizacao(self):
        item_real = self._dropdown_item_personalizar.currentText()
        if not item_real:
            return
        apelido = self._campo_apelido.text().strip()
        if apelido:
            radial_menu.definir_apelido(item_real, apelido)
        else:
            radial_menu.remover_apelido(item_real)

        emoji = self._campo_icone_item.text().strip()
        if self._imagem_icone_escolhida:
            try:
                radial_menu.definir_icone_customizado_arquivo(item_real, self._imagem_icone_escolhida)
            except OSError as erro:
                avisar(self, "Imagem não copiada", str(erro))
                return
        elif emoji:
            radial_menu.definir_icone_customizado(item_real, emoji)
        # campo vazio sem imagem nova: mantém o ícone que já estava (pra
        # tirar, use o ✕ da lista)
        self._atualizar_lista_personalizacoes()
        self._carregar_personalizacao(item_real)

    def _remover_personalizacao(self, item_real):
        radial_menu.remover_apelido(item_real)
        radial_menu.remover_icone_customizado(item_real)
        self._atualizar_lista_personalizacoes()
        self._carregar_personalizacao(self._dropdown_item_personalizar.currentText())

    # ------------------------------------------------------------------
    # Preferências
    # ------------------------------------------------------------------
    def _construir_aba_preferencias(self):
        widget = QWidget()
        layout_externo = QVBoxLayout(widget)
        layout_externo.setContentsMargins(0, 0, 0, 0)
        scroll, layout = criar_scroll_area()
        layout_externo.addWidget(scroll)
        layout.setSpacing(14)

        # --- Atalho ---
        layout.addWidget(criar_titulo_secao("Atalho do menu", tamanho=12))
        linha_atalho = QHBoxLayout()
        atalho_atual = (self._atalho_em_uso() if self._atalho_em_uso else None) or radial_menu.obter_atalho()
        self._campo_atalho = criar_lineedit(atalho_atual)
        self._campo_atalho.setPlaceholderText("ex.: ctrl+alt+space")
        self._campo_atalho.returnPressed.connect(self._aplicar_atalho)
        linha_atalho.addWidget(self._campo_atalho, stretch=1)
        botao_atalho = criar_botao("Aplicar atalho")
        botao_atalho.clicked.connect(self._aplicar_atalho)
        linha_atalho.addWidget(botao_atalho)
        layout.addLayout(linha_atalho)
        self._descricao_atalho = criar_descricao(self._texto_atalho(atalho_atual))
        layout.addWidget(self._descricao_atalho)

        # --- Perfis ---
        layout.addWidget(criar_titulo_secao("Perfis", tamanho=12))
        layout.addWidget(criar_descricao("Cada perfil tem seus próprios favoritos, categorias e ordem da Steam. Pastas, apelidos e ícones valem pra todos."))
        linha_perfil = QHBoxLayout()
        self._dropdown_perfil = criar_dropdown(radial_menu.obter_nomes_perfis(), radial_menu.obter_perfil_atual())
        self._dropdown_perfil.currentTextChanged.connect(self._trocar_perfil)
        linha_perfil.addWidget(self._dropdown_perfil, stretch=1)
        self._campo_nome_perfil = criar_lineedit()
        self._campo_nome_perfil.setPlaceholderText("Nome do perfil")
        linha_perfil.addWidget(self._campo_nome_perfil, stretch=1)
        layout.addLayout(linha_perfil)
        linha_perfil_botoes = QHBoxLayout()
        botao_novo_perfil = criar_botao("Criar cópia do atual")
        botao_novo_perfil.clicked.connect(self._criar_perfil)
        linha_perfil_botoes.addWidget(botao_novo_perfil)
        botao_renomear_perfil = criar_botao("Renomear atual")
        botao_renomear_perfil.clicked.connect(self._renomear_perfil)
        linha_perfil_botoes.addWidget(botao_renomear_perfil)
        linha_perfil_botoes.addStretch(1)
        # ação destrutiva longe das frequentes, no fim da linha
        botao_excluir_perfil = criar_botao("Excluir atual", cor_texto="#f38ba8")
        botao_excluir_perfil.clicked.connect(self._excluir_perfil)
        linha_perfil_botoes.addWidget(botao_excluir_perfil)
        layout.addLayout(linha_perfil_botoes)

        layout.addWidget(criar_titulo_secao("Favoritos", tamanho=12))

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

        # --- Projects ---
        layout.addWidget(criar_titulo_secao("Categoria Projects", tamanho=12))
        layout.addWidget(criar_descricao(
            "Ao iniciar, o IRIS procura pastas \"Project-...\" e acrescenta à categoria Projects "
            "as que ainda não conhecia. O que você remover da categoria não volta."
        ))
        linha_proj = QHBoxLayout()
        linha_proj.addWidget(_LabelSimples("Pasta dos projetos:"))
        self._campo_pasta_projetos = criar_lineedit(radial_menu.obter_pasta_projetos())
        linha_proj.addWidget(self._campo_pasta_projetos, stretch=1)
        layout.addLayout(linha_proj)
        linha_icones = QHBoxLayout()
        linha_icones.addWidget(_LabelSimples("Pasta de ícones (Nome.png):"))
        self._campo_pasta_icones = criar_lineedit(radial_menu.obter_pasta_icones_projetos())
        self._campo_pasta_icones.setPlaceholderText("opcional")
        linha_icones.addWidget(self._campo_pasta_icones, stretch=1)
        layout.addLayout(linha_icones)
        botao_sincronizar = criar_botao("Salvar e procurar projetos agora")
        botao_sincronizar.clicked.connect(self._sincronizar_projetos)
        layout.addWidget(botao_sincronizar)

        layout.addWidget(criar_titulo_secao("Plugins", tamanho=12))
        registrados = plugin_registry.providers_registrados()
        if not registrados:
            layout.addWidget(criar_descricao("Nenhum plugin instalado neste processo."))
            # 🔥 2026-08-16 (pedido do usuário, mesma ideia aplicada na GAIA
            # pro Argus) - "tudo configurável fica no Painel", não só um
            # comando de terminal documentado no README. Só GAIA por
            # enquanto - é o único plugin que existe hoje.
            self._btn_instalar_plugin_gaia = criar_botao("Instalar integração com a GAIA")
            self._btn_instalar_plugin_gaia.clicked.connect(self._instalar_plugin_gaia)
            layout.addWidget(self._btn_instalar_plugin_gaia)
            layout.addWidget(criar_descricao("Instala plugins/iris_plugin_gaia (repo irmão) - depois de reiniciar o IRIS, categorias da GAIA aparecem no popup se ela estiver rodando."))
        else:
            disponiveis = {p.id for p in plugin_registry.disponiveis_em_cache()}
            for provider in registrados:
                disponivel = provider.id in disponiveis
                status = "disponível agora" if disponivel else "instalado, indisponível agora"
                layout.addWidget(criar_descricao(f"• {provider.rotulo_categoria}  ({provider.id})  -  {status}"))
                capacidades = ", ".join(sorted(provider.capacidades())) or "sem efeito externo declarado"
                layout.addWidget(criar_descricao(
                    f"Capacidades: {capacidades}. Timeout declarado: "
                    f"{provider.tempo_limite_segundos:g}s."
                ))

        return widget

    def _texto_atalho(self, atalho):
        return f"Em uso: {descrever_atalho(atalho)}. Aceita ctrl, alt, shift, win + uma tecla (letra, número, F1-F24, space, tab...)."

    def _aplicar_atalho(self):
        texto = self._campo_atalho.text().strip()
        if self._ao_mudar_atalho is not None:
            ok, resultado = self._ao_mudar_atalho(texto)
        else:
            from iris.core.atalho import AtalhoInvalido, interpretar_atalho
            try:
                _, _, resultado = interpretar_atalho(texto)
                radial_menu.salvar_atalho(resultado)
                ok = True
            except AtalhoInvalido as erro:
                ok, resultado = False, str(erro)
        if not ok:
            avisar(self, "Atalho não aplicado", resultado)
            return
        self._campo_atalho.setText(resultado)
        self._descricao_atalho.setText(self._texto_atalho(resultado))

    def _recarregar_dados_do_perfil(self):
        self._atualizar_lista_favoritos()
        self._dropdown_add_favorito.clear()
        self._dropdown_add_favorito.addItems(self._itens_disponiveis_para_favoritar())
        self._atualizar_lista_categorias()
        self._preencher_checkboxes_itens_categoria()
        self._atualizar_lista_steam()

    def _recarregar_dropdown_perfis(self):
        self._dropdown_perfil.blockSignals(True)
        self._dropdown_perfil.clear()
        self._dropdown_perfil.addItems(radial_menu.obter_nomes_perfis())
        self._dropdown_perfil.setCurrentText(radial_menu.obter_perfil_atual())
        self._dropdown_perfil.blockSignals(False)

    def _trocar_perfil(self, nome):
        if not nome or nome == radial_menu.obter_perfil_atual():
            return
        radial_menu.definir_perfil_atual(nome)
        self._recarregar_dados_do_perfil()

    def _nome_perfil_digitado(self):
        nome = self._campo_nome_perfil.text().strip()
        if not nome:
            avisar(self, "Perfil sem nome", "Digite o nome do perfil no campo ao lado.")
            return None
        if nome in radial_menu.obter_nomes_perfis():
            avisar(self, "Nome em uso", f"Já existe um perfil chamado '{nome}'.")
            return None
        return nome

    def _criar_perfil(self):
        nome = self._nome_perfil_digitado()
        if not nome:
            return
        radial_menu.criar_perfil(nome, copiar_de=radial_menu.obter_perfil_atual())
        radial_menu.definir_perfil_atual(nome)
        self._campo_nome_perfil.clear()
        self._recarregar_dropdown_perfis()
        self._recarregar_dados_do_perfil()

    def _renomear_perfil(self):
        nome = self._nome_perfil_digitado()
        if not nome:
            return
        radial_menu.renomear_perfil(radial_menu.obter_perfil_atual(), nome)
        self._campo_nome_perfil.clear()
        self._recarregar_dropdown_perfis()

    def _excluir_perfil(self):
        atual = radial_menu.obter_perfil_atual()
        if len(radial_menu.obter_nomes_perfis()) <= 1:
            avisar(self, "Único perfil", "Não dá pra excluir o único perfil que existe.")
            return
        if not confirmar_acao(self, "Excluir perfil", f"Excluir o perfil '{atual}' com os favoritos e categorias dele?"):
            return
        radial_menu.remover_perfil(atual)
        self._recarregar_dropdown_perfis()
        self._recarregar_dados_do_perfil()

    def _sincronizar_projetos(self):
        pasta = self._campo_pasta_projetos.text().strip()
        icones = self._campo_pasta_icones.text().strip()
        if pasta and not os.path.isdir(pasta):
            avisar(self, "Pasta inválida", "A pasta dos projetos não existe neste PC.")
            return
        if icones and not os.path.isdir(icones):
            avisar(self, "Pasta inválida", "A pasta de ícones não existe neste PC.")
            return
        padrao = os.path.dirname(armazenamento.RAIZ_PROJETO)
        radial_menu.salvar_pasta_projetos("" if os.path.normcase(pasta) == os.path.normcase(padrao) else pasta)
        radial_menu.salvar_pasta_icones_projetos(icones)
        adicionados = radial_menu.sincronizar_categoria_projetos()
        self._atualizar_lista_categorias()
        self._preencher_checkboxes_itens_categoria()
        if adicionados:
            avisar(self, "Projects atualizada", f"Adicionado(s): {', '.join(adicionados)}.")
        else:
            avisar(self, "Projects", "Nenhum projeto novo encontrado.")

    def _instalar_plugin_gaia(self):
        self._btn_instalar_plugin_gaia.setEnabled(False)
        self._btn_instalar_plugin_gaia.setText("Instalando...")

        def _trabalho():
            raiz_repo = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            caminho_plugin = os.path.join(raiz_repo, "plugins", "iris_plugin_gaia")
            if not os.path.isdir(caminho_plugin):
                raise RuntimeError(f"Pasta \"{caminho_plugin}\" não encontrada.")
            # 🔥 "uv pip" (não "python -m pip") - `uv venv` cria o venv SEM
            # pip por padrão (achado real testando isto agora - o venv do
            # IRIS não tem `pip` nenhum instalado, `python -m pip` falha com
            # "No module named pip"). `cwd=raiz_repo` pra `uv` achar o
            # `.venv` daqui sozinho, sem precisar apontar o interpretador
            # manualmente.
            resultado = subprocess.run(
                ["uv", "pip", "install", "-e", caminho_plugin],
                cwd=raiz_repo, capture_output=True, text=True,
            )
            if resultado.returncode != 0:
                raise RuntimeError(resultado.stderr.strip() or "uv pip install falhou sem mensagem de erro.")

        def _ao_terminar(_resultado, erro):
            self._btn_instalar_plugin_gaia.setEnabled(True)
            self._btn_instalar_plugin_gaia.setText("Instalar integração com a GAIA")
            if erro:
                avisar(self, "Plugin GAIA", f"Erro ao instalar: {erro}")
                return
            avisar(self, "Plugin GAIA", "Plugin instalado. Reinicie o IRIS pra ele ser carregado.")

        executar_em_thread(_trabalho, _ao_terminar, parent=self)


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
