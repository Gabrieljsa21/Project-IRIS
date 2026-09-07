"""Testa o contrato de capacidades sem abrir Qt, rede ou processo."""

from iris.plugins.base import ActionProvider
from iris.plugins import registry


class _Provider(ActionProvider):
    id = "teste"
    rotulo_categoria = "Teste"
    tempo_limite_segundos = 3

    def __init__(self):
        self.executados = []

    def capacidades(self):
        return {"rede", "gravar_arquivo"}

    def confirmacao_para(self, item):
        return "Confirmar?" if item == "sensivel" else None

    def esta_disponivel(self):
        return True

    def listar_subitens(self):
        return ["normal", "sensivel"]

    def executar(self, item):
        self.executados.append(item)


def main():
    provider = _Provider()
    registry.registrar_provider(provider)
    assert registry.executar_provider(provider, "normal") is True
    assert registry.executar_provider(provider, "sensivel") is False
    assert registry.executar_provider(provider, "sensivel", lambda _m: False) is False
    assert registry.executar_provider(provider, "sensivel", lambda _m: True) is True
    assert provider.executados == ["normal", "sensivel"]

    class _Invalido(_Provider):
        id = "invalido"

        def capacidades(self):
            return {"teletransporte"}

    try:
        registry.registrar_provider(_Invalido())
    except ValueError:
        pass
    else:
        raise AssertionError("capacidade desconhecida deveria ser rejeitada")
    print("OK: manifesto, fail-closed e confirmação de plugins validados")


if __name__ == "__main__":
    main()
