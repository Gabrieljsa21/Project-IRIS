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

**Anime Tracker mudou pra `plugins/iris_plugin_moirai` em 2026-08-24** - o
Assistente de Animes deixou de ser hospedado pela GAIA (agora é processo
próprio, Project-MOIRAI, porta 8768) - ver `TODO.md`/`providers.py` daquele
pacote pro que era pendente aqui (segue pendente lá).

## Fora de escopo mesmo depois dos endpoints acima

- Nenhuma normalização de config entre o `data/menu_radial_config.json` da
  GAIA (perfis/uso antigos) e o do IRIS - são bancos de dados de launcher
  INDEPENDENTES desde a extração; migrar favoritos manualmente é trabalho do
  usuário, uma vez, ao adotar o IRIS.
