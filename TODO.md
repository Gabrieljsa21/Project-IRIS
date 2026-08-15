# TODO - Project-IRIS

## Pendências cross-repo (dependem de mudanças no lado da GAIA)

- **Endpoint/IPC pra "Funções da Gaia" e "Anime Tracker" ainda não existe do
  lado da GAIA** - o plugin `plugins/iris_plugin_gaia/` já tem as classes
  `FuncoesGaiaProvider`/`AnimeTrackerProvider` prontas como stub
  (`esta_disponivel()` sempre `False`), mas fazer as categorias aparecerem
  de verdade no popup exige trabalho no repo `Project G.A.I.A` (expor um
  endpoint HTTP ou outro IPC equivalente) - ver detalhe completo, endpoint
  por endpoint, em `plugins/iris_plugin_gaia/TODO.md`. Isso é trabalho no
  OUTRO repo, não algo pra resolver aqui.
- **"Animações do VTube Studio"** - mesma categoria de pendência (endpoint
  faltando do lado da GAIA), ver `plugins/iris_plugin_gaia/TODO.md`.

## Pendências do core (podem ser resolvidas só neste repo)

- Sem testes automatizados ainda - a extração foi validada só por
  `python -m py_compile` + import estático dos módulos sem dependência de
  Qt/Windows (ver seção "Verificação" do `ARQUITETURA.md`/relatório de
  extração). Rodar o popup de verdade (hotkey, clique, drag) ainda não foi
  feito num ambiente com display interativo.
- Tela de Configurações (`iris/ui/settings_window.py`) cobre CRUD básico
  (favoritos/categorias/pastas/Steam/preferências) mas não replica toda a
  riqueza do modal equivalente da GAIA (`ui/qt_modais/menu_radial.py`, não
  portado - fora do escopo desta extração): sem gerenciamento de perfis
  múltiplos na UI (a API em `core/radial_menu.py` já suporta,
  `criar_perfil`/`remover_perfil`/`renomear_perfil`), sem editor de
  apelidos/ícones customizados na UI (a API também já suporta).
- Indicador contextual de "downloads ativos" (existia no Menu Radial
  original, injetado como favorito temporário quando havia download de
  anime em andamento) foi removido do core na extração - era 100%
  específico do Anime Tracker da GAIA. Se fizer sentido reintroduzir algo
  parecido de forma genérica (um plugin "empurrando" um item contextual pro
  anel de favoritos), precisa de um hook novo em `ActionProvider`
  (`iris/plugins/base.py`) - não existe hoje.
- Ícone próprio do IRIS ainda não existe - a bandeja do sistema e o
  `pyproject.toml` reaproveitam o ícone genérico do botão do Menu Radial
  (`assets/icones/menu_radial_botao.png`, vendorizado da GAIA).

## Sem pendência (decisões já resolvidas na extração)

- Config split (core vs. plugin) - ver `ARQUITETURA.md`, seção "Config
  split".
- Automação de apps (kill-switch) - removida por completo (2026-08-15, ver
  `ARQUITETURA.md`, ponto #4) - era o kill-switch de ação autônoma da IA da
  GAIA, sem utilidade real pro clique manual do launcher.
