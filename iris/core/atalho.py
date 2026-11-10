# -*- coding: utf-8 -*-
"""Interpretação do texto de um atalho global ("ctrl+alt+space") para os
códigos que o `RegisterHotKey` do Windows espera. Função pura, sem Qt nem
Win32 - o registro de verdade fica em `iris/ui/atalho_global.py`.

Entrada tolerante (maiúsculas, espaços, sinônimos em português, "espaço" com
ou sem acento); saída sempre no mesmo formato canônico."""

import unicodedata

ATALHO_PADRAO = "ctrl+alt+space"

MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008

_MODIFICADORES = {
    "ctrl": ("ctrl", MOD_CONTROL), "control": ("ctrl", MOD_CONTROL), "strg": ("ctrl", MOD_CONTROL),
    "alt": ("alt", MOD_ALT),
    "shift": ("shift", MOD_SHIFT),
    "win": ("win", MOD_WIN), "windows": ("win", MOD_WIN), "super": ("win", MOD_WIN), "meta": ("win", MOD_WIN),
}
_ORDEM_MODIFICADORES = ["ctrl", "alt", "shift", "win"]

_TECLAS = {
    "space": 0x20, "espaco": 0x20, "spacebar": 0x20,
    "tab": 0x09, "enter": 0x0D, "return": 0x0D, "esc": 0x1B, "escape": 0x1B,
    "backspace": 0x08, "delete": 0x2E, "del": 0x2E, "insert": 0x2D, "ins": 0x2D,
    "home": 0x24, "end": 0x23, "pageup": 0x21, "pagedown": 0x22,
    "left": 0x25, "up": 0x26, "right": 0x27, "down": 0x28,
    "esquerda": 0x25, "cima": 0x26, "direita": 0x27, "baixo": 0x28,
    "pause": 0x13, "printscreen": 0x2C, "capslock": 0x14,
    "'": 0xDE, "`": 0xC0, "-": 0xBD, "=": 0xBB, ",": 0xBC, ".": 0xBE, "/": 0xBF, ";": 0xBA,
    "[": 0xDB, "]": 0xDD, "\\": 0xDC,
}
_NOME_CANONICO = {"espaco": "space", "spacebar": "space", "return": "enter", "escape": "esc",
                  "del": "delete", "ins": "insert", "esquerda": "left", "cima": "up",
                  "direita": "right", "baixo": "down"}


class AtalhoInvalido(ValueError):
    pass


def _sem_acento(texto):
    return "".join(c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c))


def interpretar_atalho(texto):
    """Devolve (modificadores, codigo_tecla, texto_canonico). Exige ao menos
    um modificador e exatamente uma tecla - um atalho global sem modificador
    sequestraria a tecla no sistema inteiro."""
    partes = [p for p in _sem_acento(str(texto or "")).lower().replace(" ", "").split("+") if p]
    if not partes:
        raise AtalhoInvalido("Atalho vazio.")
    modificadores = 0
    nomes_mod = set()
    tecla = None
    for parte in partes:
        if parte in _MODIFICADORES:
            nome, codigo = _MODIFICADORES[parte]
            nomes_mod.add(nome)
            modificadores |= codigo
            continue
        if tecla is not None:
            raise AtalhoInvalido("Use só uma tecla além dos modificadores (ex.: ctrl+alt+space).")
        tecla = parte
    if tecla is None:
        raise AtalhoInvalido("Falta a tecla (ex.: ctrl+alt+space).")
    if not modificadores:
        raise AtalhoInvalido("Inclua ao menos um modificador (ctrl, alt, shift ou win).")

    if len(tecla) == 1 and (tecla.isascii() and tecla.isalnum()):
        codigo = ord(tecla.upper())
    elif tecla.startswith("f") and tecla[1:].isdigit() and 1 <= int(tecla[1:]) <= 24:
        codigo = 0x70 + int(tecla[1:]) - 1
    elif tecla in _TECLAS:
        codigo = _TECLAS[tecla]
        tecla = _NOME_CANONICO.get(tecla, tecla)
    else:
        raise AtalhoInvalido(f"Tecla desconhecida: '{tecla}'.")

    canonico = "+".join([m for m in _ORDEM_MODIFICADORES if m in nomes_mod] + [tecla])
    return modificadores, codigo, canonico


def descrever_atalho(texto):
    """Texto para exibição: "Ctrl+Alt+Espaço"."""
    try:
        _, _, canonico = interpretar_atalho(texto)
    except AtalhoInvalido:
        return str(texto)
    nomes = {"space": "Espaço", "ctrl": "Ctrl", "alt": "Alt", "shift": "Shift", "win": "Win"}
    return "+".join(nomes.get(p, p.upper() if len(p) <= 3 else p.capitalize()) for p in canonico.split("+"))
