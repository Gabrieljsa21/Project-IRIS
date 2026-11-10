# -*- coding: utf-8 -*-
"""Avisos ao usuário e registro em arquivo.

O IRIS roda em `pythonw` (sem console): `print` não chega a ninguém. Tudo o
que o usuário precisa saber passa por `avisar_usuario` (balão da bandeja,
ligado por `iris/main.py` via `definir_notificador`) e tudo fica registrado
em `data/iris.log`. Sem dependência de Qt aqui."""

import logging
import os
from logging.handlers import RotatingFileHandler

from iris.core.armazenamento import PASTA_DADOS

registro = logging.getLogger("iris")
_notificador = None


def configurar_registro():
    if registro.handlers:
        return
    registro.setLevel(logging.INFO)
    try:
        os.makedirs(PASTA_DADOS, exist_ok=True)
        manipulador = RotatingFileHandler(
            os.path.join(PASTA_DADOS, "iris.log"), maxBytes=512_000, backupCount=2, encoding="utf-8",
        )
        manipulador.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        registro.addHandler(manipulador)
    except OSError:
        registro.addHandler(logging.NullHandler())


def definir_notificador(funcao):
    """`funcao(mensagem)` mostra o aviso na tela (balão da bandeja)."""
    global _notificador
    _notificador = funcao


def avisar_usuario(mensagem):
    """Registra e mostra ao usuário. Seguro sem notificador (testes, boot)."""
    registro.warning(mensagem)
    if _notificador is not None:
        try:
            _notificador(mensagem)
        except Exception:
            registro.exception("Falha ao mostrar aviso na bandeja")
