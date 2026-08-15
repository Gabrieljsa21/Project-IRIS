# -*- coding: utf-8 -*-
"""Entry point standalone do IRIS - sobe a própria `QApplication`, registra o
hotkey global (Ctrl+Alt+Espaço, mesma tecla de sempre) e um ícone na bandeja
do sistema com acesso à tela de Configurações. Roda inteiramente sozinho, sem
nenhuma dependência da GAIA - se o pacote de plugin opcional
`iris_plugin_gaia` estiver instalado (`pip install -e plugins/iris_plugin_gaia`),
suas categorias aparecem automaticamente no popup quando a GAIA estiver de
pé; sem o plugin instalado, o popup funciona igual, só sem essas categorias.

Padrão de marshalling entre threads: `keyboard.add_hotkey` roda o callback na
THREAD DO HOOK de teclado, nunca na thread do Qt - abrir/fechar um QWidget
fora da thread dona dele é um bug clássico (trava intermitente, não erro
imediato). `IrisApp` é um `QObject` com um `Signal` (`menu_radial_solicitado`)
conectado a um slot que roda na GUI thread; `Signal.emit()` é seguro de
chamar de qualquer thread (Qt enfileira a entrega sozinho quando emissor e
receptor moram em threads diferentes) - mesmo padrão documentado em
`ARQUITETURA.md` (baseado no que `Project G.A.I.A/assistant/run.py` +
`ui/qt_painel.py` já fazem, portado aqui de forma independente, sem importar
nada de lá)."""
import importlib
import os
import sys

import keyboard
from PySide6.QtCore import QObject, Signal, QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from iris.ui.qt_widgets import aplicar_estilo_global

HOTKEY_MENU_RADIAL = "ctrl+alt+space"

# Pacotes de plugin OPCIONAIS a tentar importar/registrar no boot - nenhum
# import direto (`iris_plugin_gaia`) aqui em cima, de propósito: o core nunca
# pode falhar por causa de um plugin ausente/quebrado.
_PLUGINS_OPCIONAIS = ["iris_plugin_gaia"]


class IrisApp(QObject):
    menu_radial_solicitado = Signal()

    def __init__(self):
        super().__init__()
        self.menu_radial_solicitado.connect(self._mostrar_menu_radial)
        self.tray_icon = None

    def _mostrar_menu_radial(self):
        from iris.ui.menu_radial_qt import mostrar_menu_radial_qt
        mostrar_menu_radial_qt()

    def solicitar_menu_radial(self):
        """Chamado pelo hotkey global - roda na thread do hook de teclado,
        nunca na thread do Qt."""
        self.menu_radial_solicitado.emit()

    def abrir_configuracoes(self):
        from iris.ui.settings_window import JanelaConfiguracoes
        janela = JanelaConfiguracoes()
        janela.exec()

    def montar_bandeja(self, app):
        caminho_icone = os.path.join(os.path.dirname(__file__), "..", "assets", "icones", "menu_radial_botao.png")
        icone = QIcon(caminho_icone) if os.path.exists(caminho_icone) else app.style().standardIcon(app.style().SP_ComputerIcon)

        self.tray_icon = QSystemTrayIcon(icone)
        self.tray_icon.setToolTip("IRIS - Ctrl+Alt+Espaço abre o menu radial")

        menu = QMenu()
        acao_menu = menu.addAction("Abrir menu radial agora")
        acao_menu.triggered.connect(self._mostrar_menu_radial)
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


def _carregar_plugins_opcionais():
    """Tenta importar cada pacote de `_PLUGINS_OPCIONAIS` e chamar sua função
    `registrar()` - qualquer erro (pacote não instalado, ou instalado mas
    quebrado) é silenciosamente ignorado, o IRIS core nunca deixa de subir
    por causa de um plugin."""
    for nome_pacote in _PLUGINS_OPCIONAIS:
        try:
            modulo = importlib.import_module(nome_pacote)
            registrar = getattr(modulo, "registrar", None)
            if callable(registrar):
                registrar()
                print(f" [SISTEMA] IRIS: plugin '{nome_pacote}' registrado.")
        except ImportError:
            continue
        except Exception as e:
            print(f" [SISTEMA] IRIS: plugin '{nome_pacote}' instalado, mas falhou ao registrar: {e}")


def main():
    os.makedirs("data", exist_ok=True)

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    aplicar_estilo_global(app)

    iris_app = IrisApp()
    iris_app.montar_bandeja(app)

    _carregar_plugins_opcionais()

    keyboard.add_hotkey(HOTKEY_MENU_RADIAL, iris_app.solicitar_menu_radial)
    print(f" [SISTEMA] IRIS pronto - {HOTKEY_MENU_RADIAL} abre o menu radial. Ícone na bandeja pra Configurações/Sair.")

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
