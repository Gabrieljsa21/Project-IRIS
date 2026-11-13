"""Canal de comandos e modo sem ícone (0.5.0), sem Qt."""
import socket
import threading

import pytest

from iris.core import canal
from iris.main import sem_icone_na_bandeja


@pytest.fixture
def canal_em_porta_livre(monkeypatch):
    sonda = socket.socket()
    sonda.bind((canal.HOST, 0))
    porta = sonda.getsockname()[1]
    sonda.close()
    monkeypatch.setattr(canal, "PORTA", porta)
    servidor = canal.reservar_porta()
    recebidos = []
    chegou = threading.Event()

    def _ao_receber(comando):
        recebidos.append(comando)
        chegou.set()

    canal.atender(servidor, _ao_receber)
    yield recebidos, chegou
    servidor.close()


def testar_interpretar_tolerante():
    assert canal.interpretar(" ABRIR_MENU \r\n") == "abrir_menu"
    assert canal.interpretar("configuracoes") == "configuracoes"
    assert canal.interpretar("rm -rf") is None
    assert canal.interpretar("") is None


def testar_comandos_chegam_e_respondem(canal_em_porta_livre):
    recebidos, chegou = canal_em_porta_livre
    assert canal.enviar("ping") == "ok"
    assert recebidos == []  # ping não vira ação
    assert canal.enviar("abrir_menu") == "ok"
    assert chegou.wait(2)
    assert recebidos == ["abrir_menu"]
    assert canal.enviar("formatar disco").startswith("erro")
    assert recebidos == ["abrir_menu"]


def testar_segunda_instancia_e_barrada(canal_em_porta_livre):
    with pytest.raises(canal.InstanciaJaRodando):
        canal.reservar_porta()


def testar_sem_iris_ouvindo(monkeypatch):
    sonda = socket.socket()
    sonda.bind((canal.HOST, 0))
    porta = sonda.getsockname()[1]
    sonda.close()
    monkeypatch.setattr(canal, "PORTA", porta)
    assert canal.enviar("ping", timeout=0.3) is None


def testar_variavel_sem_icone():
    assert sem_icone_na_bandeja({"IRIS_SEM_ICONE_BANDEJA": "1"})
    assert not sem_icone_na_bandeja({"IRIS_SEM_ICONE_BANDEJA": "0"})
    assert not sem_icone_na_bandeja({})
