# IRIS - arquitetura consolidada

Launcher radial pra Windows, extraído do "Menu Radial" que vivia embutido no
processo/Painel da [GAIA](../Project%20G.A.I.A) (`Project G.A.I.A/assistant`,
`ui/menu_radial_qt.py` + `features/radial_menu/radial_menu.py`). Nasceu de
uma feature de produto da GAIA, mas é desenhado desde o início como
**projeto separado**, com repo próprio - usável sozinho por qualquer pessoa
que só quer um launcher radial, sem a GAIA inteira (voz, Discord, LLM,
avatar), e integrável dentro dela como um plugin a mais.

Este documento registra as decisões tomadas na extração (2026-08) - a
investigação de acoplamento no código-fonte da GAIA que motivou cada corte
listado abaixo.

## Estado atual (2026-08)

Extração inicial completa. Portado e **funcional**: popup radial (geometria,
paginação, busca, drag-to-reorder, ícones customizados, apelidos, cores por
ângulo), persistência (perfis/favoritos/categorias/pastas/recentes/uso),
app launcher genérico (apps fixos + escaneados + manuais, jogos da Steam,
atalhos do Menu Iniciar), monitor de hardware (CPU/RAM/GPU), sistema de
plugins (interface + registry) e uma tela de Configurações própria (a GAIA
nunca teve uma standalone - sempre dependeu do Painel dela, que não foi
portado). Do plugin opcional da GAIA, só **Avatar (Overlay)** está
funcional de verdade; os outros 3 (Funções da Gaia, Animações do VTube
Studio, Anime Tracker) são stubs documentados - ver seção própria abaixo e
`plugins/iris_plugin_gaia/TODO.md`.

## Por que separar

O Menu Radial original tinha 4 pontos de acoplamento reais com a GAIA (não
só "importa o mesmo dicionário de apps" - chamada Python direta no mesmo
processo, API HTTP local, e um import de scraping/automação de terceiro
serviço). Um launcher genérico ("abrir qualquer coisa no PC") não deveria
carregar nenhum desses 4 pontos só pra existir - a decisão foi extrair um
CORE 100% livre de GAIA, e mover os 4 pontos pra um plugin opcional
separado, instalável à parte.

## Os 4 pontos de acoplamento extraídos

Investigados a fundo no código-fonte de `Project G.A.I.A/assistant/ui/
menu_radial_qt.py` antes de qualquer porte. Cada um virou uma classe
`ActionProvider` (`iris/plugins/base.py`) dentro de
`plugins/iris_plugin_gaia/iris_plugin_gaia/providers.py`:

| # | Ponto original | Categoria no popup | Provider | Estado |
|---|---|---|---|---|
| 1 | `_abrir_funcao_gaia` - chamada Python DIRETA em `PainelQt.instancia_atual` (só funciona no MESMO processo) | ⚙️ Funções da Gaia | `FuncoesGaiaProvider` | Stub |
| 2 | `_chamar_overlay`/`_ativar_animacao`/`_reagir` - API HTTP local (porta 8765) + `VTubeStudioClient` (websocket direto) | 🖥️ Avatar (Overlay) / 🎭 Animações do VTube Studio | `AvatarOverlayProvider` / `AnimacoesVTSProvider` | Overlay **funcional**; Animações stub |
| 3 | `_adicionar_anime_da_area_de_transferencia`/`_assistir_anime_por_titulo` - `anime_tracker` (scraping + qBittorrent) | 🎬 Anime Tracker | `AnimeTrackerProvider` | Stub |
| 4 | `brain_store.obter_automacao_apps_habilitada`/`obter_anime_pasta_downloads` - 2 flags lidas do cérebro central da GAIA (~4786 linhas) só pra isso | (kill-switch de automação, sem categoria própria) | `obter_anime_pasta_downloads` fica pendente no plugin (Anime Tracker); o kill-switch foi removido | Removido do core (2026-08-15) |

O ponto #2 virou DUAS categorias porque, na origem, elas usam mecanismos
diferentes: Avatar Overlay fala HTTP (fácil de reaproveitar de outro
processo, sem mudar nada do lado da GAIA); Animações fala WebSocket direto
via um cliente Python que só existe dentro do processo da GAIA (não dá pra
importar de outro pacote) - ver `plugins/iris_plugin_gaia/TODO.md` pro que
falta pra destravar isso.

O ponto #4 é o único que não virou plugin. "Automação de apps
ligada/desligada" primeiro virou uma flag própria do core (sem depender de
`brain_store`), mas foi **removida por completo em seguida** (2026-08-15,
decisão do usuário) - o flag original na GAIA é o kill-switch que impede a
LLM/agente de abrir/fechar programas sozinha (via `<APP:abrir:alvo>`,
proteção contra ação autônoma indesejada); reaproveitar essa mesma trava pro
clique manual num favorito do popup não fazia sentido no IRIS (o clique já
é intencional, não existe "IA decidindo sozinha" pra proteger num launcher
sem LLM). `obter_anime_pasta_downloads` (a outra metade do ponto #4) é
específico do Anime Tracker - continua pendente junto com esse stub.

## Sistema de plugins

- **`iris/plugins/base.py::ActionProvider`** - interface mínima:
  `id`, `rotulo_categoria`, `esta_disponivel()`, `listar_subitens()`,
  `executar(item)`, `subitens_favoritaveis()` (default `False`). O popup
  (`iris/ui/menu_radial_qt.py`) só conhece essa interface - nunca importa um
  plugin específico.
- **`iris/plugins/registry.py`** - `registrar_provider`/`providers_disponiveis`/
  `provider_por_categoria`, populado por `iris/main.py` no boot (tenta
  `importlib.import_module("iris_plugin_gaia")` + chama `registrar()`; falha
  de import = plugin não instalado, silenciosamente ignorado).
- **`plugins/iris_plugin_gaia/`** - pacote SEPARADO (próprio
  `pyproject.toml`), só quem tem a GAIA instala. Ver `TODO.md` dele pro
  estado de cada provider.

## O que NÃO saiu do core (generalizações intencionais)

As 3 constantes sentinela e categorias abaixo já eram genéricas na origem
(sem nenhum acoplamento de GAIA) e continuam no core:

- `ITEM_PASTAS`/`ITEM_RECENTES`/`ITEM_STEAM` (`iris/core/radial_menu.py`) -
  atalhos de pasta, histórico de uso e jogos da Steam são conceitos de
  launcher genérico, não de GAIA.
- Categorias criadas pelo próprio usuário (`obter_categorias()`) - sempre
  foram dado puro, sem nenhuma dependência.

## Config split

`data/menu_radial_config.json` (core) guarda só dado de "launcher":
perfis/favoritos/categorias/pastas/recentes/apelidos/ícones/uso/limites/
automação. Nenhum dado específico de plugin (ex.: reações da Gala no VTube
Studio, que existiam no original) fica aqui - se um plugin precisar de
config própria no futuro, ganha arquivo/namespace separado, carregado só
quando o plugin estiver ativo (nenhum implementado ainda, já que os 3
providers pendentes são stubs sem estado nenhum pra guardar).

## Vendorização de `qt_widgets.py`

`iris/ui/qt_widgets.py` é um subconjunto vendorizado de
`Project G.A.I.A/assistant/ui/qt_widgets.py` - só o que a tela de
Configurações (`iris/ui/settings_window.py`) e o bootstrap da
`QApplication` (`iris/main.py`) realmente usam (`ModalBase`, `Switch`,
`CheckboxQuadrado`, `LinhaSelecionavel`, dropdown customizado, spinbox
cápsula, scroll area arrastável, helpers de card/botão/campo). Widgets do
arquivo original usados só por OUTRAS telas do Painel da GAIA (`FlowLayout`
de cards, slider, link clicável) não foram trazidos.

O popup radial em si (`iris/ui/menu_radial_qt.py`) é `QPainter` puro e nunca
usou `qt_widgets.py`, na GAIA ou aqui - só a tela de Configurações usa.

## Tecnologia

- **PySide6** - própria `QApplication` (`iris/main.py`), nunca compartilhada
  com outro processo (diferente do Argus, que roda dentro da mesma
  `QApplication` do Painel quando embutido na GAIA - o IRIS não tem
  "modo embutido", só standalone + plugin opcional via HTTP).
- **`keyboard`** - hotkey global (`Ctrl+Alt+Espaço`, mesma tecla de sempre),
  registrado em `iris/main.py`. Callback roda na thread do hook, marshallado
  pra GUI thread via `Signal` Qt (`IrisApp.menu_radial_solicitado`) - mesmo
  padrão que `run.py`/`ui/qt_painel.py` já usam na GAIA, reimplementado aqui
  de forma independente (sem importar nada de lá).
- **`psutil`/`pywin32`** - app launcher (processos, atalhos do Menu
  Iniciar) e monitor de hardware (CPU/RAM); GPU via `nvidia-smi` (subprocess,
  sem dependência de pip extra).

## Distribuição

- Repo próprio no GitHub pessoal do usuário
  (`github.com/Gabrieljsa21/Project-IRIS`, privado) - não dentro do repo da
  GAIA, que outras pessoas não conseguem acessar.
- `plugins/iris_plugin_gaia/` é um pacote pip separado dentro do MESMO repo
  (monorepo) - decisão consciente: o plugin só faz sentido acompanhando o
  core (mesma versão de `ActionProvider`), e mora fisicamente perto do
  código que ele documenta o acoplamento com.
