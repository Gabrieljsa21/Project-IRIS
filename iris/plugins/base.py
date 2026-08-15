# -*- coding: utf-8 -*-
"""Interface minima que um plugin do IRIS implementa pra adicionar uma
categoria extra ao popup radial - sem o core (`iris/`) precisar saber nada
sobre quem implementa (GAIA ou qualquer outra coisa). Ver `registry.py` pro
registro consultado pelo popup, e `plugins/iris_plugin_gaia/` pro unico
consumidor real hoje."""

from abc import ABC, abstractmethod


class ActionProvider(ABC):
    """Cada instancia vira UMA categoria extra no anel de favoritos, exibida
    só quando `esta_disponivel()` responde True. `id` precisa ser unico entre
    todos os providers registrados (usado pelo registry e pra roteamento de
    clique); `rotulo_categoria` é o texto (com emoji, mesmo padrão visual do
    resto do popup) mostrado de verdade na fatia."""

    id: str
    rotulo_categoria: str

    @abstractmethod
    def esta_disponivel(self) -> bool:
        """Chamado toda vez que o popup abre (nunca cacheado pelo core) -
        decide se a categoria aparece agora. Ex.: checar se um serviço HTTP
        local responde, ou se um pacote opcional está instalado."""
        raise NotImplementedError

    @abstractmethod
    def listar_subitens(self) -> list:
        """Rótulos (com emoji, mesmo padrão do resto do popup) exibidos DENTRO
        da categoria - resolvido em runtime, nunca fixo. Lista vazia é válida
        (o popup mostra a categoria mesmo sem subitens ainda). Um item cujo
        rótulo comece com "ℹ️ " ou "⏳ " é tratado pelo popup como AVISO (sem
        ação nenhuma associada, clique nele não chama `executar`) - use esse
        prefixo pra mensagens tipo "nada disponível agora"/"carregando"."""
        raise NotImplementedError

    @abstractmethod
    def executar(self, item: str) -> None:
        """Chamado quando o usuário clica em `item` (um dos rótulos devolvidos
        por `listar_subitens`) - nunca bloqueia a GUI thread por muito tempo;
        trabalho de rede/IO deve rodar em thread própria, igual o resto do
        popup já faz (ver `iris/ui/menu_radial_qt.py`)."""
        raise NotImplementedError

    def subitens_favoritaveis(self) -> bool:
        """True se os subitens desta categoria fazem sentido favoritar
        isoladamente no anel principal (clique do meio) - False (padrão) pra
        categorias de AÇÃO (ex.: "Funções da Gaia", "Avatar Overlay"), onde
        cada subitem é um comando, não um app/pasta lançável sozinho."""
        return False
