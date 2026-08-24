# TODO - iris-plugin-moirai

Ver `README.md` pro que já é funcional hoje (Anime Tracker, capa como
ícone).

## Pendente

- **Pasta de downloads configurável** (`obter_anime_pasta_downloads`,
  `moirai/config.py`) - o Menu Radial original tinha um item "📁 Abrir
  pasta de downloads de animes" que lia essa configuração; o provider ainda
  não expõe isso (precisaria de mais um endpoint `GET /pasta_downloads` do
  lado do MOIRAI, ou aceitar que esse item específico não faz sentido fora
  do processo local dele). Baixa prioridade - não bloqueia o resto do
  provider. Herdado de `iris_plugin_gaia/TODO.md`, onde era o mesmo pendente
  antes da extração.
