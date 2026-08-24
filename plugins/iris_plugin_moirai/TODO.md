# TODO - iris-plugin-moirai

Instalação: instalar o pacote `iris` (raiz do repo) primeiro, depois este
pacote no mesmo venv (`pip install -e .` na raiz, depois
`pip install -e plugins/iris_plugin_moirai`). Sem `iris` instalado, o import
de `iris.plugins.registry`/`iris.plugins.base` em `iris_plugin_moirai/
__init__.py` falha e `iris/main.py` simplesmente ignora o plugin (nunca
derruba o core).

## Funcional hoje

- **Anime Tracker** (`AnimeTrackerProvider`, extraído de `iris_plugin_gaia`
  em 2026-08-24) - fala com o Project-MOIRAI (porta 8768, `IRIS_MOIRAI_URL`
  sobrescrevível via variável de ambiente): `GET /anime/tenho_interesse`
  lista os títulos rastreados, `POST /anime/adicionar` (corpo `{"url":
  ...}`, link já copiado) adiciona um anime novo (timeout de 30s - o
  endpoint é síncrono do lado do MOIRAI, faz scraping + qBittorrent de
  verdade), `POST /anime/assistir/<titulo>` abre o próximo episódio
  baixado.

## Pendente

- **Pasta de downloads configurável** (`obter_anime_pasta_downloads`,
  `moirai/config.py`) - o Menu Radial original tinha um item "📁 Abrir
  pasta de downloads de animes" que lia essa configuração; o provider ainda
  não expõe isso (precisaria de mais um endpoint `GET /pasta_downloads` do
  lado do MOIRAI, ou aceitar que esse item específico não faz sentido fora
  do processo local dele). Baixa prioridade - não bloqueia o resto do
  provider. Herdado de `iris_plugin_gaia/TODO.md`, onde era o mesmo pendente
  antes da extração.
