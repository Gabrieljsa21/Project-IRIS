# TODO - iris-plugin-gaia

Instalação: instalar o pacote `iris` (raiz do repo) primeiro, depois este
pacote no mesmo venv (`pip install -e .` na raiz, depois
`pip install -e plugins/iris_plugin_gaia`). Sem `iris` instalado, o import de
`iris.plugins.registry`/`iris.plugins.base` em `iris_plugin_gaia/__init__.py`
falha e `iris/main.py` simplesmente ignora o plugin (nunca derruba o core).

## Funcional hoje

- **Avatar (Overlay)** (`AvatarOverlayProvider`, `providers.py`) - reaproveita
  a API HTTP já existente do overlay da GAIA (`vtuber_overlay.py`, porta
  8765), sem nenhuma mudança do lado dela. `esta_disponivel()` faz um TCP
  connect na porta (sem chamar rota nenhuma) pra decidir se a categoria
  aparece no popup agora.
- **Animações do VTube Studio** (`AnimacoesVTSProvider`, 2026-08-21) - usa os
  2 endpoints novos no MESMO servidor do overlay (porta 8765): `GET /vts/
  expressoes` (lista real, via `VTubeStudioClient.listar_expressoes()`) e
  `POST /vts/expressao/<nome>` (ativa, via `ativar_expressao_manual`).
- **Funções da Gaia** (`FuncoesGaiaProvider`, 2026-08-21) - usa o servidor
  HTTP novo do processo principal da GAIA (`integrations/iris_bridge.py`,
  porta 8766, sempre ativo): `GET /funcoes` lista os rótulos, `POST /funcao`
  (corpo `{"rotulo": ...}`) chama o método correspondente em
  `PainelQt.instancia_atual`.
- **Anime Tracker** (`AnimeTrackerProvider`, 2026-08-21) - mesmo servidor da
  porta 8766: `GET /anime/tenho_interesse` lista os títulos rastreados,
  `POST /anime/adicionar` (corpo `{"url": ...}`, link já copiado - mesmo
  fluxo do Menu Radial original da GAIA) adiciona um anime novo, `POST
  /anime/assistir/<titulo>` abre o próximo episódio baixado.

## Pendente

- **Pasta de downloads configurável** (`obter_anime_pasta_downloads`,
  `brain_store.py` da GAIA) - o Menu Radial original tinha um item "📁 Abrir
  pasta de downloads de animes" que lia essa configuração; `AnimeTrackerProvider`
  ainda não expõe isso (precisaria de mais um endpoint `GET /anime/pasta_downloads`
  do lado da GAIA, ou aceitar que esse item específico não faz sentido fora
  do processo local dela). Baixa prioridade - não bloqueia o resto do
  provider.

## Fora de escopo mesmo depois dos endpoints acima

- Nenhuma normalização de config entre o `data/menu_radial_config.json` da
  GAIA (perfis/uso antigos) e o do IRIS - são bancos de dados de launcher
  INDEPENDENTES desde a extração; migrar favoritos manualmente é trabalho do
  usuário, uma vez, ao adotar o IRIS.
