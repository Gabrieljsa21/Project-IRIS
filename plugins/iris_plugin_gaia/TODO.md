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

## Stubs - pendente de trabalho do LADO DA GAIA (cross-repo, fora do escopo
desta extração)

Os 3 providers abaixo estão implementados como classe (`ActionProvider`
válido, registrado normalmente), mas `esta_disponivel()` sempre devolve
`False` - a categoria nunca aparece no popup até o trabalho descrito abaixo
ser feito no repo `Project G.A.I.A`:

1. **Animações do VTube Studio** (`AnimacoesVTSProvider`) - a GAIA fala com o
   VTube Studio via `integrations.vtubestudio.vtube_studio_client.
   VTubeStudioClient` (websocket direto, autenticação própria do VTS) - esse
   módulo mora dentro do processo da GAIA, não dá pra importar de outro
   processo/pacote. **Precisa**: a GAIA expor um endpoint HTTP (ex.: no mesmo
   servidor do overlay, porta 8765) tipo `GET /vts/expressoes` (lista os
   arquivos `.exp3.json` disponíveis) e `POST /vts/expressao/<nome>` (ativa
   uma expressão) - depois disso, este provider vira uma cópia quase 1:1 do
   `AvatarOverlayProvider`.

2. **Funções da Gaia** (`FuncoesGaiaProvider`) - o original
   (`_abrir_funcao_gaia`, `menu_radial_qt.py` da GAIA) fazia uma chamada
   Python DIRETA em `PainelQt.instancia_atual` do MESMO processo (abrir um
   modal do Painel - Discord, Chaves, Relógio, Personas, Vozes,
   Notificações, Menu Radial, Animes). Rodando o IRIS num processo separado,
   isso é estruturalmente impossível sem algum IPC novo. **Precisa**: decidir
   um mecanismo (endpoint HTTP que dispara `metodo()` no Painel já rodando,
   named pipe, ou simplesmente aceitar que "Funções da Gaia" só abre modais
   que fazem sentido abrir remotamente) antes de implementar de verdade.

3. **Anime Tracker** (`AnimeTrackerProvider`) - o original
   (`_adicionar_anime_da_area_de_transferencia`/`_assistir_anime_por_titulo`)
   fala direto com `features.anime_tracker.anime_tracker` (scraping de sites
   de fansub + integração com qBittorrent), sem nenhuma API HTTP hoje.
   **Precisa**: expor pelo menos `GET /anime/tenho_interesse` (lista de
   títulos) + `POST /anime/adicionar` (link copiado) + `POST /anime/assistir/
   <chave>` do lado da GAIA antes de portar a lógica de verdade pra cá.

Nenhum dos 3 acima deve ser "resolvido" só fingindo disponibilidade (ex.:
sempre `True` sem endpoint nenhum por trás) - a categoria simplesmente não
aparece até o endpoint existir de verdade, evitando um clique morto no popup.

## Fora de escopo mesmo depois dos endpoints acima

- Nenhuma normalização de config entre o `data/menu_radial_config.json` da
  GAIA (perfis/uso antigos) e o do IRIS - são bancos de dados de launcher
  INDEPENDENTES desde a extração; migrar favoritos manualmente é trabalho do
  usuário, uma vez, ao adotar o IRIS.
