# TODO - Project IRIS

## Pendências do core (podem ser resolvidas só neste repo)

- Cobertura automatizada ainda é parcial: o plugin do MOIRAI já possui teste
  isolado do contrato HTTP/menu, mas o core, a hotkey e as interações do popup
  (clique e arraste) ainda dependem de cobertura própria. Rodar o popup de
  verdade continua pendente num ambiente com display interativo.
- Tela de Configurações (`iris/ui/settings_window.py`) cobre CRUD básico
  (favoritos/categorias/pastas/Steam/preferências) mas não replica toda a
  riqueza do modal equivalente da GAIA (`ui/qt_modais/menu_radial.py`, não
  portado - fora do escopo desta extração): sem gerenciamento de perfis
  múltiplos na UI (a API em `core/radial_menu.py` já suporta,
  `criar_perfil`/`remover_perfil`/`renomear_perfil`), sem editor de
  apelidos/ícones customizados na UI (a API também já suporta).
- Manifesto de capacidades dos plugins (`iris/plugins/base.py`/`registry.py`,
  2026-09-07) não obriga um provider com capacidade sensível a implementar
  `confirmacao_para` (herda `None` da base e executa sem confirmação
  nenhuma) - a checagem hoje só rejeita capacidade desconhecida/timeout
  inválido, não força o autor do provider a se comportar. `tempo_limite_
  segundos`/`cancelar()` também não têm enforcement nenhum do framework,
  são só validados no registro e exibidos na tela de Plugins - cada
  provider precisa implementar seu próprio timeout/cancelamento na prática.
  Achado numa revisão (ver `docs/ARQUITETURA.md`, seção "Capacidades e
  autorização").
- Indicador contextual de "downloads ativos" (existia no Menu Radial
  original, injetado como favorito temporário quando havia download de
  anime em andamento) foi removido do core na extração - era 100%
  específico do Anime Tracker da GAIA. Se fizer sentido reintroduzir algo
  parecido de forma genérica (um plugin "empurrando" um item contextual pro
  anel de favoritos), precisa de um hook novo em `ActionProvider`
  (`iris/plugins/base.py`) - não existe hoje.

## Sem pendência (decisões já resolvidas na extração)

- Config split (core vs. plugin) - ver `ARQUITETURA.md`, seção "Config
  split".
- Automação de apps (kill-switch) - removida por completo (2026-08-15, ver
  `ARQUITETURA.md`, ponto #4) - era o kill-switch de ação autônoma da IA da
  GAIA, sem utilidade real pro clique manual do launcher.
