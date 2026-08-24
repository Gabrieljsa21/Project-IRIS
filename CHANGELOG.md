# Changelog

Histórico de alto nível do que muda no Project-IRIS, por versão. Detalhe técnico
completo de cada decisão está em `ARQUITETURA.md`.

Versionamento: [Semantic Versioning](VERSIONAMENTO_CHANGELOG.md). A extração
inicial do Menu Radial (scaffold, port do core, plugin da GAIA, documentação -
ver `ARQUITETURA.md` pro histórico completo) é anterior a este arquivo e não
foi documentada retroativamente; o histórico versionado começa em `0.1.0`.

## [Unreleased]

### Novidades
- Botão "Instalar integração com a GAIA" (Configurações → Preferências → Plugins), quando nenhum plugin está registrado - instala `plugins/iris_plugin_gaia` via `uv pip install -e` sem precisar de terminal.
- `AnimacoesVTSProvider`/`FuncoesGaiaProvider`/`AnimeTrackerProvider` (plugin `iris_plugin_gaia`) saem do estado de stub - passam a chamar endpoints HTTP novos do lado da GAIA (porta 8765 do overlay pra Animações; porta 8766 nova, sempre ativa, pra Funções da Gaia e Anime Tracker). Ver `ARQUITETURA.md` e `plugins/iris_plugin_gaia/TODO.md`.
- Guarda de instância única (porta 8767 local, mesmo padrão de `_garantir_instancia_unica` da GAIA) - a GAIA agora pode lançar o IRIS sozinha (Menu Radial migrado pra consumir o IRIS em vez de manter cópia própria), então rodar duas instâncias por engano (manual + lançada pela GAIA) passou a ser um risco real, não só teórico.
- **Novo pacote `plugins/iris_plugin_moirai`** (2026-08-24) - `AnimeTrackerProvider` saiu de `iris_plugin_gaia` pra aqui, porque o Assistente de Animes deixou de ser hospedado pela GAIA (agora processo próprio, Project-MOIRAI, porta 8768). Mesmo contrato HTTP de sempre, sobrescrevível via `IRIS_MOIRAI_URL` - registrado em `iris/main.py::_PLUGINS_OPCIONAIS` junto com `iris_plugin_gaia`. Validado rodando os 2 processos juntos (IRIS + MOIRAI), provider respondendo com dados reais.
- **Fase 2 do MOIRAI (2026-08-24)**: `POST /anime/adicionar` do lado do MOIRAI parou de disparar o download sozinho (agora é `POST /anime/baixar_pendentes`, chamada separada) - `AnimeTrackerProvider.executar` (item "Adicionar Anime") passou a chamar os 2 endpoints em sequência, mesmo comportamento final de sempre pro usuário.

### Alterado
- Ícone da bandeja do sistema (`assets/icones/menu_radial_botao.png`) trocado pela arte oficial nova do IRIS.

## [0.2.1] - 2026-08-15: Segurança

### Segurança
- Repositório passou a ser público - `.gitignore` agora exclui `.env` explicitamente (só `.env.example`, sem dado real, era versionado). Conferido o histórico completo do Git antes da publicação: nenhuma chave/token real chegou a ser commitado em nenhum momento.

## [0.2.0] - 2026-08-15: Corrige popup bloqueado, aninhamento de categorias e renderização parcial

### Novidades
- Botão "Importar de outro menu_radial_config.json..." na aba Pastas.
- Aba Categorias permite aninhar pastas E outras categorias como itens (o motor do popup já suportava aninhamento desde sempre, só a tela de Configurações não expunha a opção).
- Margem do popup passou a ser dinâmica, calculada pela profundidade REALMENTE alcançável a partir dos favoritos atuais - sem nenhuma categoria favoritada, o popup abre exatamente onde o cursor está, sem margem sobrando.

### Correções
- Popup radial ficava travado (aparecia mas não recebia clique nenhum) sempre que a tela de Configurações estava aberta - `janela.exec()` sempre vira modal de aplicação independente da flag configurada; trocado por `.show()` não-modal.
- Eixo Y do popup ignorava a posição real do cursor, sempre abrindo perto do centro vertical do monitor.
- Anel do popup renderizava só 1 fatia (a favorita sob o cursor) em vez das 4, especificamente ao abrir o popup logo depois de interagir com a tela de Configurações. **Causa raiz real**: o próprio hotkey que abre o popup termina em Espaço (`Ctrl+Alt+Espaço`) - esse Espaço físico às vezes vaza pro popup recém-focado como um `keyPressEvent` normal, e o código tratava qualquer espaço digitado como início de busca, filtrando os favoritos pra só os que têm espaço no nome. Corrigido ignorando espaço como primeiro caractere do filtro. Três tentativas anteriores de "consertar composição do DWM" (raise+repaint, nudge de posição, hide+show) foram um beco sem saída - revertidas na mesma correção, não existia bug de composição nenhum.

## [0.1.1] - 2026-08-15: Paleta e limpeza

### Correções
- Paleta de cores do porte inicial tinha um acento ciano que não existe na identidade visual da GAIA - revertido pro acento dourado e pras cores originais do popup.
- Removido o toggle de automação de apps (kill-switch) herdado da GAIA - lá existe pra impedir a LLM de agir sozinha; não fazia sentido pro clique manual num favorito do IRIS, que já é sempre intencional.

## [0.1.0] - 2026-08-15: Inicialização sem console

### Novidades
- `iniciar_iris.bat` + `iniciar_iris_oculto.vbs` + `criar_atalho_desktop.vbs` (mesmo padrão de inicialização sem console do Project-ARGUS).
