# -*- coding: utf-8 -*-
"""Atalho global do IRIS, em dois modos.

1. NATIVO (preferido): `RegisterHotKey` do Windows. O sistema entrega só a
   combinação pedida (`WM_HOTKEY`) na fila de mensagens da thread do Qt - sem
   gancho de teclado, sem thread extra, e a tecla do atalho não vaza pro
   popup recém-aberto.
2. COMPARTILHADO (reserva): `RegisterHotKey` é exclusivo - se OUTRO programa
   já registrou a mesma combinação, o Windows recusa (erro 1409). Achado real
   em 2026-11-09: `ctrl+alt+space`, o atalho de sempre do IRIS, já estava
   registrado por outro programa na máquina. Pra não quebrar o atalho que o
   usuário já usa, nesse caso (e só nele) entra o gancho da biblioteca
   `keyboard`, que observa as teclas sem exclusividade, como era até a 0.3.0.
   O callback do gancho roda numa thread própria; a `_Ponte` (um `Signal`)
   traz a chamada de volta pra thread do Qt.

A interpretação do texto ("ctrl+alt+space") é pura e fica em
`iris/core/atalho.py`."""
import ctypes
from ctypes import wintypes

from PySide6.QtCore import QAbstractNativeEventFilter, QCoreApplication, QObject, QTimer, Signal

from iris.core.atalho import AtalhoInvalido, interpretar_atalho
from iris.core.avisos import registro

WM_HOTKEY = 0x0312
MOD_NOREPEAT = 0x4000
_ID_ATALHO = 0xA115

MODO_NATIVO = "nativo"
MODO_COMPARTILHADO = "compartilhado"


class _Ponte(QObject):
    acionado = Signal()


class AtalhoGlobal(QAbstractNativeEventFilter):
    """`registrar(texto)` devolve (ok, mensagem). O atalho anterior só é
    abandonado depois que o novo foi aceito."""

    def __init__(self, ao_acionar):
        super().__init__()
        self._ponte = _Ponte()
        self._ponte.acionado.connect(ao_acionar)
        self._registrado = None
        self._modo = None
        self._gancho = None
        self._user32 = ctypes.windll.user32
        self._user32.RegisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT]
        self._user32.RegisterHotKey.restype = wintypes.BOOL
        self._user32.UnregisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int]
        QCoreApplication.instance().installNativeEventFilter(self)

    @property
    def atalho_atual(self):
        return self._registrado

    @property
    def modo(self):
        return self._modo

    def _ativar(self, texto):
        """Tenta o modo nativo e, se a combinação já for de outro programa, o
        compartilhado. Devolve (modo, gancho) ou (None, None)."""
        modificadores, tecla, canonico = interpretar_atalho(texto)
        if self._user32.RegisterHotKey(None, _ID_ATALHO, modificadores | MOD_NOREPEAT, tecla):
            return MODO_NATIVO, None
        try:
            import keyboard
            gancho = keyboard.add_hotkey(canonico.replace("win", "windows"), self._ponte.acionado.emit)
            return MODO_COMPARTILHADO, gancho
        except Exception:
            registro.exception("Atalho %s recusado pelo Windows e o modo compartilhado falhou", canonico)
            return None, None

    def _desativar(self):
        if self._modo == MODO_NATIVO:
            self._user32.UnregisterHotKey(None, _ID_ATALHO)
        elif self._modo == MODO_COMPARTILHADO and self._gancho is not None:
            try:
                import keyboard
                keyboard.remove_hotkey(self._gancho)
            except Exception:
                registro.exception("Falha ao remover o gancho do atalho")
        self._registrado = self._modo = self._gancho = None

    def registrar(self, texto):
        try:
            _, _, canonico = interpretar_atalho(texto)
        except AtalhoInvalido as erro:
            return False, str(erro)
        if canonico == self._registrado:
            return True, canonico
        anterior = self._registrado
        self._desativar()
        modo, gancho = self._ativar(canonico)
        if modo is None:
            if anterior is not None:
                modo_ant, gancho_ant = self._ativar(anterior)
                if modo_ant is not None:
                    self._registrado, self._modo, self._gancho = anterior, modo_ant, gancho_ant
            return False, f"Não consegui registrar o atalho {canonico}."
        self._registrado, self._modo, self._gancho = canonico, modo, gancho
        if modo == MODO_COMPARTILHADO:
            registro.info("Atalho %s já registrado por outro programa; usando o modo compartilhado.", canonico)
        return True, canonico

    def liberar(self):
        self._desativar()

    def nativeEventFilter(self, tipo_evento, mensagem):
        if tipo_evento in (b"windows_generic_MSG", b"windows_dispatcher_MSG"):
            msg = wintypes.MSG.from_address(int(mensagem))
            if msg.message == WM_HOTKEY and msg.wParam == _ID_ATALHO:
                # Fora do filtro nativo: abrir janela de dentro dele reentra
                # no despacho de mensagens do Windows.
                QTimer.singleShot(0, self._ponte.acionado.emit)
                return True, 0
        return False, 0
