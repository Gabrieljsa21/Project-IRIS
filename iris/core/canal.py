# -*- coding: utf-8 -*-
"""Canal de comandos local do IRIS (0.5.0).

A porta 8767 já era a trava de instância única: o IRIS só fazia `bind` nela
para descobrir se outro IRIS estava rodando. Agora ela também escuta, e
quem está na mesma máquina (a GAIA) manda uma linha de texto e recebe outra:

    abrir_menu      abre o menu radial (não fecha se já estiver aberto)
    configuracoes   abre a janela de Configurações
    ping            só confirma que o IRIS está de pé

Resposta: "ok", ou "erro: <motivo>". Uma conexão, um comando. Só aceita
conexões de 127.0.0.1. Sem Qt aqui: quem sobe o canal entrega uma função que
recebe o comando e o leva para a thread da interface (ver `iris/main.py`)."""

import socket
import threading

from iris.core.avisos import registro

HOST = "127.0.0.1"
PORTA = 8767
COMANDOS = ("abrir_menu", "configuracoes", "ping")
_TAMANHO_MAXIMO = 256


class InstanciaJaRodando(Exception):
    """A porta já está em uso: outro IRIS está rodando."""


def reservar_porta():
    """Faz o `bind` (e o `listen`) na porta do canal. É a trava de instância
    única: levanta `InstanciaJaRodando` se outro IRIS já estiver nela."""
    servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        servidor.bind((HOST, PORTA))
    except OSError as erro:
        servidor.close()
        raise InstanciaJaRodando(str(erro)) from erro
    servidor.listen(4)
    return servidor


def interpretar(linha):
    """Texto recebido -> comando conhecido, ou None. Tolerante a maiúsculas,
    espaços e quebra de linha."""
    comando = (linha or "").strip().lower()
    return comando if comando in COMANDOS else None


def atender(servidor, ao_receber):
    """Aceita conexões numa thread própria. `ao_receber(comando)` é chamado
    nessa thread; precisa ser seguro para isso (um `Signal.emit`)."""

    def _uma_conexao(conexao):
        with conexao:
            conexao.settimeout(2)
            try:
                dados = conexao.recv(_TAMANHO_MAXIMO)
            except OSError:
                return
            comando = interpretar(dados.decode("utf-8", errors="replace"))
            if comando is None:
                conexao.sendall(b"erro: comando desconhecido\n")
                return
            if comando != "ping":
                try:
                    ao_receber(comando)
                except Exception:
                    registro.exception("Falha ao repassar o comando '%s'", comando)
                    conexao.sendall(b"erro: falha interna\n")
                    return
            conexao.sendall(b"ok\n")

    def _laco():
        while True:
            try:
                conexao, endereco = servidor.accept()
            except OSError:
                return  # servidor fechado ao sair
            if endereco[0] != HOST:
                conexao.close()
                continue
            _uma_conexao(conexao)

    threading.Thread(target=_laco, daemon=True, name="iris-canal").start()


def enviar(comando, timeout=1.0):
    """Lado cliente (testes e scripts): manda um comando e devolve a resposta,
    ou None se o IRIS não estiver ouvindo."""
    try:
        with socket.create_connection((HOST, PORTA), timeout=timeout) as conexao:
            conexao.sendall((comando + "\n").encode("utf-8"))
            return conexao.recv(_TAMANHO_MAXIMO).decode("utf-8").strip()
    except OSError:
        return None
