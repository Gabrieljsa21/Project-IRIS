# Changelog

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/).

## [Unreleased]

### Adicionado

- Extração inicial do Menu Radial que vivia embutido na GAIA (`Project
  G.A.I.A/assistant`) pra um projeto independente, `Project-IRIS`. Ver
  `ARQUITETURA.md` pro histórico completo da extração.
- Core (`iris/`): popup radial (`ui/menu_radial_qt.py`), persistência
  (`core/radial_menu.py`), app launcher genérico (`core/app_launcher.py` +
  `core/apps_scanner.py`), monitor de hardware (`core/hardware_monitor.py`),
  sistema de plugins (`plugins/base.py` + `plugins/registry.py`) - zero
  dependência de GAIA.
- Entry point standalone (`iris/main.py`) - própria `QApplication`, hotkey
  global `Ctrl+Alt+Espaço`, ícone na bandeja do sistema.
- Tela de Configurações própria (`iris/ui/settings_window.py`) - favoritos,
  categorias, pastas, jogos da Steam e preferências do core, criada do zero
  (a GAIA nunca teve uma versão standalone dessa tela).
- Widgets Qt vendorizados de `Project G.A.I.A/assistant/ui/qt_widgets.py`
  (`iris/ui/qt_widgets.py`) - só o subconjunto usado pela tela de
  Configurações.
- Plugin opcional `plugins/iris_plugin_gaia/` - implementa os 4 pontos de
  acoplamento identificados na extração como `ActionProvider`. Só **Avatar
  (Overlay)** está funcional (reaproveita a API HTTP existente da GAIA,
  porta 8765); **Funções da Gaia**, **Animações do VTube Studio** e **Anime
  Tracker** são stubs documentados em `plugins/iris_plugin_gaia/TODO.md`,
  pendentes de endpoint/IPC do lado da GAIA.
- `data/menu_radial_config.example.json` - schema de referência (sem dado
  pessoal real).
- `README.md`, `ARQUITETURA.md`, `TODO.md`, `pyproject.toml`, `.gitignore`.
- `iniciar_iris.bat` + `iniciar_iris_oculto.vbs` + `criar_atalho_desktop.vbs` -
  mesmo padrão de inicialização sem console do `Project-ARGUS`: o `.bat` sobe
  o IRIS via `pythonw` (sem janela pro app), o `.vbs` esconde o console do
  próprio `.bat`, e o atalho da Área de Trabalho aponta pro `.vbs`.
- Botão "Importar de outro menu_radial_config.json..." na aba Pastas
  (`radial_menu.importar_pastas`) - lê a chave `"pastas"` de um config
  compatível (ex.: o do Menu Radial da GAIA, mesmo schema) e importa só as
  que existem neste PC, ignorando o resto.
- Aba Categorias agora permite aninhar pastas E outras categorias como
  itens (igual a GAIA - "2026-08-07, pedido do usuário: pode permitir mais
  de 2 anéis") - a extração original só listava apps como itens
  selecionáveis, uma lacuna do porte (o motor do popup já suportava
  aninhamento desde sempre, só a tela de Configurações não expunha a
  opção). Categoria sendo editada fica de fora da própria lista (evita
  auto-referência direta); ciclos indiretos continuam protegidos em
  runtime pelo popup (`_cadeia_categorias_atual`).

- Toggle "Automação de apps" (kill-switch) - na GAIA esse flag existe pra
  impedir a LLM/agente de abrir/fechar programas sozinha; reaproveitá-lo
  pro clique manual num favorito do IRIS não fazia sentido (o clique já é
  intencional). Removido de `core/radial_menu.py`, `ui/menu_radial_qt.py` e
  da tela de Configurações.

### Corrigido

- Paleta de cores do porte inicial estava com um acento ciano (`#7dd3fc`)
  que não existe na identidade visual da GAIA - revertido pro acento
  dourado (`GAIA_GOLD #d4af6a`, widgets/botões) e pras cores originais do
  popup (`#facc15` no indicador de favorito, `#a855f7` no anel do monitor
  de hardware), igual ao Menu Radial original.
- Popup radial ficava travado (aparecia mas não recebia clique nenhum)
  sempre que a tela de Configurações estava aberta - `abrir_configuracoes`
  chamava `janela.exec()`, que o Qt sempre trata como modal de aplicação
  independente da flag configurada, bloqueando input de qualquer outra
  janela do processo. Trocado por `.show()` não-modal, com a referência da
  janela guardada em `IrisApp` (senão o GC do Python derrubava a janela
  assim que a função retornava).
- Anel do popup renderiza só 1 fatia (a favorita sob o cursor) em vez das 4,
  sempre que o popup abre SOBREPONDO outra janela do próprio app (ex.: a
  tela de Configurações visível e em foco) - suspeita é o DWM do Windows só
  compondo parcialmente o 1º frame de uma janela translúcida
  (`WA_TranslucentBackground`) nesse cenário. **Ainda não confirmado como
  resolvido** - a 1ª tentativa (`raise_()` + `repaint()`) não bastou (usuário
  confirmou o mesmo erro após reiniciar); 2ª tentativa em
  `mostrar_menu_radial_qt` força um "nudge" de geometria de verdade
  (`move()` 1px e volta, já que `repaint()` sozinho é só do lado do Qt, não
  força o Windows a recompor a SUPERFÍCIE da janela) - precisa validação no
  uso real antes de considerar resolvido.
- Eixo Y do popup ignorava a posição real do cursor, sempre abrindo perto do
  centro vertical do monitor (eixo X funcionava normal) - a margem antiga
  reservava espaço pro teto TÉCNICO de aninhamento (`MAX_NIVEIS_ANINHADOS`,
  3 categorias aninhadas, 1200px), maior que a ALTURA de monitores comuns
  (1080p/1440p), o que colapsava o clamp de Y num valor fixo.
  `_margem_ancora_que_cabe` agora reserva margem pra profundidade
  REALMENTE configurada agora (`_profundidade_maxima_configurada` - conta
  categoria-dentro-de-categoria de verdade na config atual, recalculado
  toda vez que o popup abre), não o teto técnico - se só existem
  categorias de 1 nível, a margem cai de 600px pra 344px no eixo Y
  (1080p), seguindo o cursor de verdade na prática.
