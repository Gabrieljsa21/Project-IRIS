# -*- coding: utf-8 -*-
"""Entry point standalone do IRIS - sobe a própria `QApplication`, registra o
atalho global (Ctrl+Alt+Espaço por padrão, configurável) e um ícone na
bandeja do sistema com acesso à tela de Configurações. Roda inteiramente
sozinho, sem nenhuma dependência da GAIA - plugins opcionais instalados
(ver `_carregar_plugins`) acrescentam categorias ao popup quando o serviço
deles está de pé; sem plugin nenhum, o popup funciona igual.

Atalho global: `iris/ui/atalho_global.py` - `RegisterHotKey` do Windows, com
o gancho da biblioteca `keyboard` de reserva quando a combinação já pertence
a outro programa. Nos dois modos a chamada chega aqui já na thread do Qt."""
import importlib
import os
import socket
import sys
import threading
from importlib import metadata

from PySide6.QtCore import QObject
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from iris.core import armazenamento, avisos
from iris.core.atalho import ATALHO_PADRAO, descrever_atalho
from iris.core.avisos import registro
from iris.ui.qt_widgets import aplicar_estilo_global

# Plugins: descobertos pelo grupo de entry points `iris.plugins` (cada plugin
# declara no próprio `pyproject.toml` uma função `registrar`) - instalar um
# plugin novo não exige editar o core. A lista abaixo é só compatibilidade:
# pacotes instalados ANTES de declararem o entry point continuam carregando
# pelo nome até serem reinstalados.
GRUPO_ENTRY_POINTS = "iris.plugins"
_PLUGINS_LEGADOS = ["iris_plugin_gaia", "iris_plugin_moirai"]

# Instância única (2026-08-23): reservar uma porta TCP local só pra esta
# instância - se já estiver ocupada, outro IRIS já está rodando. Importa
# porque a GAIA também sobe o IRIS sozinha (`integrations/iris_bridge.py::
# garantir_iris_rodando`); sem a guarda, uma segunda execução duplicava
# processo, ícone de bandeja e atalho.
PORTA_INSTANCIA_UNICA = 8767
_socket_instancia_unica = None


def _garantir_instancia_unica():
    global _socket_instancia_unica
    _socket_instancia_unica = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        _socket_instancia_unica.bind(("127.0.0.1", PORTA_INSTANCIA_UNICA))
    except OSError:
        registro.info("Já existe um IRIS rodando (porta %s ocupada); encerrando esta instância.", PORTA_INSTANCIA_UNICA)
        sys.exit(1)


class IrisApp(QObject):
    def __init__(self):
        super().__init__()
        self.tray_icon = None
        self.atalho = None
        self._janela_config = None

    def alternar_menu_radial(self):
        from iris.ui.menu_radial_qt import mostrar_menu_radial_qt
        if mostrar_menu_radial_qt() == "sem_favoritos":
            # Atalho sem nada pra mostrar não pode parecer quebrado: leva o
            # usuário direto pra onde ele resolve.
            avisos.avisar_usuario("Nenhum favorito ativo no menu. Abri as Configurações pra você escolher.")
            self.abrir_configuracoes()

    def aplicar_atalho(self, texto):
        """Registra o atalho e, se aceito, salva. Devolve (ok, mensagem) -
        usado no boot e pela tela de Configurações."""
        from iris.core import radial_menu
        ok, resultado = self.atalho.registrar(texto)
        if ok:
            if radial_menu.obter_atalho() != resultado:
                radial_menu.salvar_atalho(resultado)
            if self.tray_icon is not None:
                self.tray_icon.setToolTip(f"IRIS - {descrever_atalho(resultado)} abre o menu radial")
        return ok, resultado

    def abrir_configuracoes(self):
        """Não-modal de propósito - `.exec()` deixaria o app inteiro (inclusive
        o popup radial) sem receber clique nenhum enquanto a janela estivesse
        aberta. Guarda a referência em `self` pra não ser coletada pelo GC do
        Python assim que a função retorna."""
        if self._janela_config is not None:
            self._janela_config.show()
            self._janela_config.raise_()
            self._janela_config.activateWindow()
            return
        from iris.ui.settings_window import JanelaConfiguracoes
        self._janela_config = JanelaConfiguracoes(
            ao_mudar_atalho=self.aplicar_atalho,
            atalho_em_uso=lambda: self.atalho.atalho_atual,
        )
        self._janela_config.finished.connect(self._ao_fechar_configuracoes)
        self._janela_config.show()

    def _ao_fechar_configuracoes(self, *_args):
        self._janela_config = None

    def montar_bandeja(self, app):
        caminho_icone = os.path.join(armazenamento.RAIZ_PROJETO, "assets", "icones", "menu_radial_botao.png")
        icone = QIcon(caminho_icone) if os.path.exists(caminho_icone) else app.style().standardIcon(app.style().SP_ComputerIcon)

        self.tray_icon = QSystemTrayIcon(icone)
        self.tray_icon.setToolTip("IRIS")

        menu = QMenu()
        acao_menu = menu.addAction("Abrir menu radial agora")
        acao_menu.triggered.connect(self.alternar_menu_radial)
        acao_config = menu.addAction("Configurações...")
        acao_config.triggered.connect(self.abrir_configuracoes)
        menu.addSeparator()
        acao_sair = menu.addAction("Sair")
        acao_sair.triggered.connect(app.quit)

        self.tray_icon.setContextMenu(menu)
        self.tray_icon.activated.connect(
            lambda motivo: self.abrir_configuracoes() if motivo == QSystemTrayIcon.DoubleClick else None
        )
        self.tray_icon.show()
        avisos.definir_notificador(
            lambda mensagem: self.tray_icon.showMessage("IRIS", mensagem, QSystemTrayIcon.Information, 6000)
        )


def _carregar_plugins():
    """Chama o `registrar()` de cada plugin instalado. Qualquer erro (pacote
    ausente ou quebrado) fica só no log - o core nunca deixa de subir por
    causa de um plugin."""
    carregados = set()
    try:
        pontos = list(metadata.entry_points(group=GRUPO_ENTRY_POINTS))
    except Exception:
        registro.exception("Falha ao listar entry points de plugins")
        pontos = []
    for ponto in pontos:
        modulo = ponto.value.split(":", 1)[0]
        try:
            ponto.load()()
            carregados.add(modulo)
            registro.info("Plugin '%s' registrado (entry point).", ponto.name)
        except Exception:
            registro.exception("Plugin '%s' falhou ao registrar", ponto.name)
            carregados.add(modulo)
    for nome_pacote in _PLUGINS_LEGADOS:
        if nome_pacote in carregados:
            continue
        try:
            registrar = getattr(importlib.import_module(nome_pacote), "registrar", None)
            if callable(registrar):
                registrar()
                registro.info("Plugin '%s' registrado.", nome_pacote)
        except ImportError:
            continue
        except Exception:
            registro.exception("Plugin '%s' instalado, mas falhou ao registrar", nome_pacote)


def main():
    avisos.configurar_registro()
    _garantir_instancia_unica()

    from iris.core import radial_menu
    from iris.plugins import registry as plugin_registry
    from iris.ui.atalho_global import AtalhoGlobal

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    aplicar_estilo_global(app)

    iris_app = IrisApp()
    iris_app.montar_bandeja(app)

    try:
        adicionados = radial_menu.sincronizar_categoria_projetos()
        if adicionados:
            avisos.avisar_usuario(f"Novo(s) em Projects: {', '.join(adicionados)}.")
    except Exception:
        registro.exception("Falha ao sincronizar a categoria Projects")

    _carregar_plugins()
    # Primeira checagem de disponibilidade em segundo plano - o primeiro
    # popup já abre sabendo quais serviços estão de pé.
    threading.Thread(target=plugin_registry.atualizar_disponibilidade, daemon=True).start()

    iris_app.atalho = AtalhoGlobal(iris_app.alternar_menu_radial)
    app.aboutToQuit.connect(iris_app.atalho.liberar)
    atalho_salvo = radial_menu.obter_atalho()
    ok, mensagem = iris_app.aplicar_atalho(atalho_salvo)
    if not ok and atalho_salvo != ATALHO_PADRAO:
        ok, _ = iris_app.aplicar_atalho(ATALHO_PADRAO)
    if ok:
        registro.info("IRIS pronto - %s abre o menu radial (modo %s).", iris_app.atalho.atalho_atual, iris_app.atalho.modo)
    else:
        avisos.avisar_usuario(f"{mensagem} Escolha outro em Configurações > Preferências; o menu continua disponível pelo ícone da bandeja.")

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
