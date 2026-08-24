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
  sobrescrevível via variável de ambiente): `GET /anime/para_assistir`
  lista só os títulos com pelo menos 1 episódio baixado pronto pra assistir
  (não todo "tenho_interesse" - clicar num título sem nada baixado seria um
  clique morto, sem seletor de episódio aqui), junto com `chave`/`capa_url`
  de cada um. `POST /anime/adicionar` (corpo `{"url": ...}`, link já
  copiado) adiciona um anime novo (timeout de 30s - o endpoint é síncrono do
  lado do MOIRAI, faz scraping + qBittorrent de verdade), `POST /anime/
  assistir/<titulo>` abre o próximo episódio baixado.
- **Capa como ícone de cada anime** (2026-08-24, pedido do usuário: "mostrar
  a capa do anime em vez de icone generico") - usa `icone_para_subitem`
  (novo método opcional em `ActionProvider`, ver `ARQUITETURA.md`), baixando
  a imagem via `GET /anime/capa/<chave>?url=<capa_url>` (o MOIRAI devolve os
  BYTES, nunca um caminho - processo/pasta diferentes) e cacheando em
  `data/moirai_capas_cache/` do lado do IRIS. Download sempre em
  BACKGROUND (nunca dentro de `listar_subitens`, que travaria o popup até a
  rede responder) - o item aparece na hora com o emoji "🎬" e troca pra capa
  sozinho assim que o download termina (repaint natural do popup).

## Pendente

- **Pasta de downloads configurável** (`obter_anime_pasta_downloads`,
  `moirai/config.py`) - o Menu Radial original tinha um item "📁 Abrir
  pasta de downloads de animes" que lia essa configuração; o provider ainda
  não expõe isso (precisaria de mais um endpoint `GET /pasta_downloads` do
  lado do MOIRAI, ou aceitar que esse item específico não faz sentido fora
  do processo local dele). Baixa prioridade - não bloqueia o resto do
  provider. Herdado de `iris_plugin_gaia/TODO.md`, onde era o mesmo pendente
  antes da extração.
