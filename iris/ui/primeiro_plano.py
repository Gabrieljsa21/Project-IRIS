# -*- coding: utf-8 -*-
"""Trazer uma janela do IRIS para o primeiro plano com o teclado nela.

O Windows só deixa um processo tomar o primeiro plano se ele for o dono da
janela da frente ou tiver recebido a última entrada do usuário. Pelo atalho
isso acontece (o Alt está pressionado), mas um comando que chega pelo canal
(`iris/core/canal.py`, vindo da GAIA) encontra o IRIS em segundo plano: o
`activateWindow` do Qt só piscava o botão na barra de tarefas, o menu abria
sem teclado (Esc e busca não funcionavam) e não fechava ao clicar fora.

`AttachThreadInput` liga temporariamente a fila de entrada desta thread à da
janela que está na frente; com as filas ligadas, o `SetForegroundWindow` é
aceito. A ligação é desfeita logo em seguida."""
import ctypes
from ctypes import wintypes

_user32 = ctypes.windll.user32
_kernel32 = ctypes.windll.kernel32
_user32.GetForegroundWindow.restype = wintypes.HWND
_user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
_user32.GetWindowThreadProcessId.restype = wintypes.DWORD
_user32.AttachThreadInput.argtypes = [wintypes.DWORD, wintypes.DWORD, wintypes.BOOL]
_user32.SetForegroundWindow.argtypes = [wintypes.HWND]
_user32.BringWindowToTop.argtypes = [wintypes.HWND]


def trazer_para_frente(widget):
    """Chamar depois do `show()`, na thread do Qt."""
    widget.raise_()
    hwnd = wintypes.HWND(int(widget.winId()))
    da_frente = _user32.GetForegroundWindow()
    thread_da_frente = _user32.GetWindowThreadProcessId(da_frente, None) if da_frente else 0
    esta_thread = _kernel32.GetCurrentThreadId()
    ligou = bool(thread_da_frente and thread_da_frente != esta_thread
                 and _user32.AttachThreadInput(esta_thread, thread_da_frente, True))
    try:
        _user32.BringWindowToTop(hwnd)
        _user32.SetForegroundWindow(hwnd)
    finally:
        if ligou:
            _user32.AttachThreadInput(esta_thread, thread_da_frente, False)
    widget.activateWindow()
