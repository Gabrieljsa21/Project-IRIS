# TODO - Project IRIS

## Pendências do core (podem ser resolvidas só neste repo)

- Cobertura automatizada das INTERAÇÕES do popup (clique, arrasto com Alt,
  teclado) ainda não está na suíte: `testes/` cobre persistência, descoberta
  de projetos, geometria, atalho, busca e o contrato de plugins, tudo sem Qt.
  As interações foram exercitadas por um roteiro fora da tela na 0.4.0, mas
  ele não faz parte do `pytest` (precisa de `QApplication`; no CI rodaria com
  `QT_QPA_PLATFORM=offscreen`).
- A busca por digitação filtra só os anéis ABERTOS (favoritos + categorias
  abertas). Um app que não está nos favoritos nem numa categoria aberta não
  aparece. Busca global (todos os apps conhecidos, resultado num anel
  próprio) daria mais valor ao teclado.
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
- `iris/ui/menu_radial_qt.py` ainda concentra desenho e interação (cerca de
  1.200 linhas). A geometria já saiu pra `geometria_radial.py`; separar o
  desenho (`_desenhar_anel`, `_pintar`) é o próximo corte natural.
- A tela de Configurações não mostra em qual modo o atalho está (nativo ou
  compartilhado); hoje isso só aparece em `data/iris.log`.

## Sem pendência (decisões já resolvidas na extração)

- Config split (core vs. plugin) - ver `ARQUITETURA.md`, seção "Config
  split".
- Automação de apps (kill-switch) - removida por completo (2026-08-15, ver
  `ARQUITETURA.md`, ponto #4) - era o kill-switch de ação autônoma da IA da
  GAIA, sem utilidade real pro clique manual do launcher.
