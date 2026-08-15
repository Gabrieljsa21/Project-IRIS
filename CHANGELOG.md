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

### Removido

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
