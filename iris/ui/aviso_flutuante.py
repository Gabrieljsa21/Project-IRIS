# -*- coding: utf-8 -*-
"""Aviso curto perto do relógio do Windows, para quando o IRIS roda sem
ícone próprio na bandeja (ligado pela GAIA, 0.5.0). Sem o ícone, o balão do
`QSystemTrayIcon.showMessage` não aparece; este aviso ocupa o mesmo lugar,
some sozinho em alguns segundos e fecha com um clique.

Um aviso por vez: um novo substitui o anterior."""
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QGuiApplication
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from iris.ui.qt_widgets import BG_COLOR, BORDA_SUTIL, FONTE_BASE, GAIA_GOLD, TEXT_COLOR

DURACAO_MS = 6000
LARGURA = 340
MARGEM = 16

_aviso_atual = None


class AvisoFlutuante(QWidget):
    def __init__(self, mensagem):
        super().__init__(None, Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setAttribute(Qt.WA_TranslucentBackground)  # cantos arredondados do fundo
        self.setFixedWidth(LARGURA)

        fundo = QWidget(self)
        fundo.setObjectName("fundo")
        fundo.setAttribute(Qt.WA_StyledBackground)
        fundo.setStyleSheet(
            f"#fundo {{ background-color: {BG_COLOR}; border: 1px solid {BORDA_SUTIL};"
            f" border-left: 3px solid {GAIA_GOLD}; border-radius: 8px; }}"
        )
        externo = QVBoxLayout(self)
        externo.setContentsMargins(0, 0, 0, 0)
        externo.addWidget(fundo)

        linha = QHBoxLayout(fundo)
        linha.setContentsMargins(14, 10, 14, 10)
        texto = QLabel(f"<b style='color:{GAIA_GOLD}'>IRIS</b><br>{mensagem}")
        texto.setWordWrap(True)
        texto.setFont(QFont(FONTE_BASE, 10))
        texto.setStyleSheet(f"color: {TEXT_COLOR}; background: transparent; border: none;")
        linha.addWidget(texto)

        self.adjustSize()
        tela = QGuiApplication.primaryScreen().availableGeometry()
        self.move(tela.right() - self.width() - MARGEM, tela.bottom() - self.height() - MARGEM)
        QTimer.singleShot(DURACAO_MS, self.close)

    def mousePressEvent(self, _evento):
        self.close()


def mostrar_aviso(mensagem):
    """Precisa rodar na thread do Qt."""
    global _aviso_atual
    if _aviso_atual is not None:
        try:
            _aviso_atual.close()
        except RuntimeError:
            pass
    _aviso_atual = AvisoFlutuante(mensagem)
    _aviso_atual.show()
