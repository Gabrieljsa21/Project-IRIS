# Changelog

Este arquivo registra as mudanças importantes do projeto. O formato segue o [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/) e as versões seguem o [Versionamento Semântico](https://semver.org/lang/pt-BR/).

Histórico de alto nível do que muda no Project IRIS, por versão. Detalhe técnico
completo de cada decisão está em `docs/ARQUITETURA.md`.

Versionamento: [Semantic Versioning](docs/VERSIONAMENTO_CHANGELOG.md). A extração
inicial do Menu Radial (scaffold, port do core, plugin da GAIA, documentação -
ver `docs/ARQUITETURA.md` pro histórico completo) é anterior a este arquivo e não
foi documentada retroativamente; o histórico versionado começa em `0.1.0`.

## [Unreleased]

## [0.5.0] - 2026-11-13

### Adicionado

- **Canal de comandos local** (`iris/core/canal.py`): a porta 8767, que já
  era a trava de instância única, agora escuta. Uma linha por conexão
  (`abrir_menu`, `configuracoes`, `ping`), resposta `ok`; só aceita
  127.0.0.1. `abrir_menu` não fecha o menu se ele já estiver aberto.
- **Modo sem ícone na bandeja:** com `IRIS_SEM_ICONE_BANDEJA=1` no ambiente
  (a GAIA 0.46.0 marca ao ligar o IRIS), o ícone próprio não aparece e o
  controle passa a ser Sentinelas → IRIS na bandeja da GAIA, como já
  acontece com a ERIS. Ligado pelo `.vbs` do IRIS, o ícone continua.
- **Aviso flutuante** (`iris/ui/aviso_flutuante.py`): sem o ícone, o balão
  do Windows não aparece; os avisos saem num cartão curto perto do relógio,
  que some em 6 s ou com um clique.

### Corrigido

- **Menu aberto por fora ficava sem teclado:** aberto por um comando com o
  IRIS em segundo plano, o Windows recusava o primeiro plano; Esc e busca
  não funcionavam e o menu não fechava ao clicar fora.
  `iris/ui/primeiro_plano.py` liga por um instante a fila de entrada à da
  janela da frente (`AttachThreadInput`) e traz menu e Configurações para a
  frente. Validado ao vivo: Esc fecha o menu aberto pelo canal e as
  Configurações abrem na frente.
- Avisos chegam à tela por sinal do Qt, de qualquer thread.

## [0.4.0] - 2026-11-10

### Corrigido

- **Configuração corrompida não é mais sobrescrita pelo padrão** - um `menu_radial_config.json` ilegível caía num `except` genérico e o IRIS gravava a estrutura padrão por cima, apagando favoritos, categorias e contagem de uso. Agora a gravação é atômica (arquivo temporário + `os.replace`), a versão anterior fica em `.bak`, e um arquivo ilegível é renomeado para `.corrompido-<data>`: o IRIS restaura o `.bak` e avisa pela bandeja. O mesmo vale para `apps_manuais.json` (`iris/core/armazenamento.py`).
- **Atualização de tela fora da thread do Qt** - as métricas de CPU/RAM/GPU chamavam `update()` do popup a partir de uma thread comum. O resultado agora volta por `Signal`.
- **Avisos que ninguém via** - o IRIS roda em `pythonw`, então "app não encontrado", "pasta não configurada", "arrastar só funciona sem busca" e erro de plugin eram `print` no vazio. Agora aparecem em balão da bandeja e ficam em `data/iris.log` (`iris/core/avisos.py`).
- **Clique abrindo o app errado** - o clique no menu usava a busca aproximada pelas duas últimas palavras, que podia achar outro app. O menu passou a exigir nome ou apelido idêntico (`find_app(..., exato=True)`).
- **Dados dependiam da pasta de onde o IRIS era iniciado** - `data/` e `assets/icones_customizados` eram caminhos relativos ao diretório atual. Agora são ancorados na raiz do repositório.
- **Atalho sem efeito com todos os favoritos desativados** - o atalho abre as Configurações e avisa, em vez de mostrar um popup vazio.

### Alterado

- **Popup sem leitura de disco por fatia** - cada repintura relia o JSON três vezes por fatia. A configuração fica em memória, validada por data de modificação e tamanho do arquivo (edição feita por fora continua sendo enxergada), e a repintura confere o disco uma vez só (`radial_menu.leitura_em_lote`). Medido com a configuração real: zero leituras de JSON em 30 repinturas e uma consulta ao disco por repintura, contra 17.
- **Brilho das fatias em cache** - o traço com desfoque só é recalculado quando muda a fatia em destaque ou o quanto ela cresceu; relógio e métricas reaproveitam a imagem.
- **Plugins não seguram mais a abertura do popup** - a disponibilidade é checada em paralelo e em segundo plano; o popup abre com o último resultado conhecido e se corrige quando a checagem termina. Categoria de plugin favoritada cujo serviço está parado some do anel até o serviço voltar, em vez de ficar como fatia sem ação.
- **Categoria Projects descoberta sozinha** - saem do código a lista fixa de projetos e os caminhos `C:\Workspace\...` e `E:\Downloads\Icones\...`. A cada início o IRIS procura pastas `Project-*` ao lado do próprio repositório (ou na pasta configurada), acha o inicializador (`iniciar_*_oculto.vbs`, `iniciar_*.bat` ou `<NOME>.bat`) e acrescenta à categoria só o que ainda não conhecia. Item removido pelo usuário não volta. Na primeira execução desta versão entraram CHRONOS, HERMES, LOKI e MIDAS.
- **Atalho global pelo `RegisterHotKey` do Windows** (`iris/ui/atalho_global.py`), sem gancho que observa todas as teclas. Quando outro programa já registrou a mesma combinação (caso real de `ctrl+alt+space` nesta máquina), o IRIS cai no modo compartilhado, com o gancho da biblioteca `keyboard`, e o atalho continua funcionando como antes.
- **Plugins descobertos por entry points** (grupo `iris.plugins`, declarado no `pyproject.toml` de cada plugin). Instalar um plugin novo não exige editar o core. Os dois plugins já instalados continuam carregando pelo nome até serem reinstalados.
- **Abertura de apps por `os.startfile`** no lugar de `start` com `shell=True`.
- Geometria do popup (raios, ângulos, hit-test, paginação) extraída para `iris/ui/geometria_radial.py`, sem Qt.

### Adicionado

- **Teclado no popup** - setas escolhem a fatia do anel mais externo, Enter ativa, Backspace (sem busca digitada) volta um anel. Com busca digitada, Enter abre o primeiro resultado.
- **Busca sem acento** - "calculo" encontra "Cálculo".
- **Atalho configurável** em Configurações > Preferências, aplicado na hora. Aceita `ctrl`, `alt`, `shift`, `win` e uma tecla, com sinônimos ("Ctrl + Alt + Espaço").
- **Perfis na tela de Configurações** - trocar, criar cópia, renomear e excluir (a API já existia).
- **Aba Personalizar** - nome exibido e ícone (emoji ou imagem) de qualquer item (a API já existia).
- **Pasta dos projetos e pasta de ícones** configuráveis em Preferências, com botão para procurar projetos na hora.
- **Testes com `pytest`** (34: persistência, descoberta de projetos, geometria, atalho, busca, contrato de plugins) e **CI** no GitHub Actions (`.github/workflows/testes.yml`).

## [0.3.0] - 2026-10-14

### Alterado

- **Backups dos ícones recortados (2026-10-01)** - `echo_recortado_old.png`, `pandora_recortado_old.png` e `siren_recortado_old.png` (`assets/icones_customizados/`) guardam as versões recortadas de ECHO, PANDORA e SIREN que a PR #32 trocou pelo emblema original. Ficam só como histórico, nada no código aponta pra eles.

- **Ícone da GAIA nítido (2026-09-26)** - o ícone da GAIA na categoria Projects era o `app_theme.ico`, que tem 16, 32, 48 e 256 px; o Qt lia o de 16 px e ampliava para 64 px no menu, e ele ficava desfocado. Agora usa o `app_theme.png` da GAIA (1254 px, mesma arte): no padrão do código (`ICONE_GAIA`, `iris/core/radial_menu.py`) e no ícone personalizado salvo (`assets/icones_customizados/gaia.png` em `data/menu_radial_config.json`).

- **Ícone do SIREN de volta ao emblema original (2026-09-26, pedido do usuário)** - `assets/icones_customizados/siren.png` (o ícone da categoria Projects, que tem prioridade sobre o `E:\Downloads\Icones\Siren.png` de `PROJETOS_PADRAO`) volta a ser a arte completa, no lugar do recorte do rosto feito no PR #28. O recorte ficou guardado como `siren_recortado_old.png`.
- **ECHO e PANDORA também de volta ao emblema original (mesmo dia)** - `echo.png` e `pandora.png` voltam a ser as artes completas de `E:\Downloads\Icones\`, no lugar dos recortes do PR #28 (guardados como `*_recortado_old.png`).

### Adicionado

- **Permissões declarativas e confirmação de plugins (2026-09-07)** - `ActionProvider` agora declara capacidades de rede, processo, leitura/escrita de arquivos e controle de janela, além de timeout positivo e cancelamento opcional. O registry rejeita capacidades desconhecidas; ações sensíveis falham fechadas sem confirmação explícita. Providers oficiais foram classificados e a tela de Plugins mostra suas capacidades e timeout. O item concluído foi removido de `docs/TODO.md`.
- **Pasta de downloads do MOIRAI voltou à categoria Watchlist** (2026-09-07): o plugin consulta `GET /pasta_downloads` e oferece o item "📁 Abrir pasta de downloads" no menu. As ações "Adicionar Anime" e "Abrir pasta" continuam visíveis mesmo quando não há episódio pronto para assistir. Validado com resposta HTTP simulada e compilação do provider.
- **SIREN adicionado à categoria "Projects"** (2026-09-06) - novo player de
  música pessoal do ecossistema (`Project-SIREN`), registrado como app
  manual (`iniciar_siren_oculto.vbs`, mesmo padrão de `app_launcher.
  adicionar_app_manual` dos demais). Sem ícone oficial ainda (emoji padrão,
  mesma situação do ECHO/PANDORA). `PROJETOS_PADRAO` atualizado pra
  reinstalações futuras também pegarem o SIREN automaticamente.
- **Categoria "Projects"** (2026-08-30, pedido do usuário: "cria uma categoria Projects, com todos os projetos q temos para abri-los facilmente") - categoria de usuário comum (não plugin), 1 item por projeto irmão do ecossistema (ARGUS/ECHO/ERIS/HESTIA/IRIS/MOIRAI/PANDORA/GAIA). Semeada 1x no boot (`radial_menu.garantir_categoria_projetos_padrao`), livre pra editar/apagar depois. **v2 no mesmo dia seguinte (2026-09-01, usuário corrigiu: "era p armazenar o inicializador de cada projeto, e deveria ter o ícone dele")** - cada item passou de "abrir a pasta" pra "rodar o `.vbs` que sobe o processo escondido" (registrado como app manual) + ganhou o ícone oficial do projeto (`E:\Downloads\Icones`); IRIS/PANDORA continuam abrindo a pasta (sem inicializador possível pros 2). ECHO/MOIRAI/HESTIA ganharam `.vbs` novo nessa mesma mudança - não existia nenhum antes. Ver `docs/ARQUITETURA.md`.
- Botão "Instalar integração com a GAIA" (Configurações → Preferências → Plugins), quando nenhum plugin está registrado - instala `plugins/iris_plugin_gaia` via `uv pip install -e` sem precisar de terminal.
- `AnimacoesVTSProvider`/`FuncoesGaiaProvider`/`AnimeTrackerProvider` (plugin `iris_plugin_gaia`) saem do estado de stub - passam a chamar endpoints HTTP novos do lado da GAIA (porta 8765 do overlay pra Animações; porta 8766 nova, sempre ativa, pra Funções da Gaia e Anime Tracker). Ver `docs/ARQUITETURA.md` e `plugins/iris_plugin_gaia/docs/TODO.md`.
- Guarda de instância única (porta 8767 local, mesmo padrão de `_garantir_instancia_unica` da GAIA) - a GAIA agora pode lançar o IRIS sozinha (Menu Radial migrado pra consumir o IRIS em vez de manter cópia própria), então rodar duas instâncias por engano (manual + lançada pela GAIA) passou a ser um risco real, não só teórico.
- **Novo pacote `plugins/iris_plugin_moirai`** (2026-08-24) - `AnimeTrackerProvider` saiu de `iris_plugin_gaia` pra aqui, porque o Assistente de Animes deixou de ser hospedado pela GAIA (agora processo próprio, Project MOIRAI, porta 8768). Mesmo contrato HTTP de sempre, sobrescrevível via `IRIS_MOIRAI_URL` - registrado em `iris/main.py::_PLUGINS_OPCIONAIS` junto com `iris_plugin_gaia`. Validado rodando os 2 processos juntos (IRIS + MOIRAI), provider respondendo com dados reais.
- **Fase 2 do MOIRAI (2026-08-24)**: `POST /anime/adicionar` do lado do MOIRAI parou de disparar o download sozinho (agora é `POST /anime/baixar_pendentes`, chamada separada) - `AnimeTrackerProvider.executar` (item "Adicionar Anime") passou a chamar os 2 endpoints em sequência, mesmo comportamento final de sempre pro usuário.
- **Anime Tracker: só "Para assistir" + capa como ícone (2026-08-24)** - a lista de subitens passou a vir de `GET /anime/para_assistir` (só quem já tem episódio baixado, evita clique morto), e cada anime ganhou a própria capa como ícone em vez do emoji "🎬" genérico pra todo mundo - baixada 1x (via MOIRAI, cacheada localmente) em background, nunca travando a abertura do popup. Motivou o método opcional `icone_para_subitem` novo em `ActionProvider` (`iris/plugins/base.py`), disponível pra qualquer provider futuro que precise de ícone dinâmico por subitem.

### Alterado

- Ícone da bandeja do sistema (`assets/icones/menu_radial_botao.png`) trocado pela arte oficial nova do IRIS.
- **Categoria "🎬 Anime Tracker" renomeada pra "🎬 Watchlist"** (2026-08-30, pedido do usuário) - só o rótulo (`AnimeTrackerProvider.rotulo_categoria`) mudou, `id`/classe continuam iguais. Rótulo antigo salvo em `favoritos`/`uso` migrado automaticamente no próximo boot, sem perder posição no círculo nem o histórico de uso. Ver `docs/ARQUITETURA.md`.

### Corrigido

- **TODO de testes atualizado para o estado real** (2026-09-07): a documentação deixou de afirmar que não existia nenhum teste automatizado depois da inclusão do teste isolado do plugin MOIRAI. A pendência permanece aberta e agora delimita corretamente o que falta cobrir: core, hotkey, popup, clique e arraste.
- **Pendência obsoleta do ícone removida do TODO** (2026-09-07): o arquivo ainda dizia que o IRIS usava a imagem genérica herdada da GAIA, embora `assets/icones/menu_radial_botao.png` já tenha sido substituído pela arte oficial e essa troca já estivesse registrada neste changelog.
- **Cache stale em `radial_menu.py` engolia edição feita por fora (2026-09-06)**
  - achado investigando "adicionei o SIREN na categoria Projects, mas ele
    sumiu de novo" - `_carregar()` guardava o dict inteiro num `_cache` de
    módulo, lido do disco só na 1ª chamada do processo; qualquer edição
    externa ao `data/menu_radial_config.json` enquanto o IRIS já estava
    rodando (ex.: um script registrando um app novo) desaparecia na
    próxima vez que QUALQUER `_salvar()` acontecesse, porque ele escrevia
    de volta o `_cache` velho por cima. Mesma classe de bug já corrigida
    antes no Argus/HESTIA/MOIRAI/ECHO ("ler 1x, nunca recarregar") - `_cache`
    removido de vez, `_carregar()` sempre lê do disco de novo. Validado:
    editar o arquivo por fora e chamar `obter_categorias()` de novo, no
    MESMO processo Python, já reflete a edição (antes não refletia).

## [0.2.1] - 2026-08-15

### Segurança
- Repositório passou a ser público - `.gitignore` agora exclui `.env` explicitamente (só `.env.example`, sem dado real, era versionado). Conferido o histórico completo do Git antes da publicação: nenhuma chave/token real chegou a ser commitado em nenhum momento.

## [0.2.0] - 2026-08-15

### Adicionado
- Botão "Importar de outro menu_radial_config.json..." na aba Pastas.
- Aba Categorias permite aninhar pastas E outras categorias como itens (o motor do popup já suportava aninhamento desde sempre, só a tela de Configurações não expunha a opção).
- Margem do popup passou a ser dinâmica, calculada pela profundidade REALMENTE alcançável a partir dos favoritos atuais - sem nenhuma categoria favoritada, o popup abre exatamente onde o cursor está, sem margem sobrando.

### Corrigido
- Popup radial ficava travado (aparecia mas não recebia clique nenhum) sempre que a tela de Configurações estava aberta - `janela.exec()` sempre vira modal de aplicação independente da flag configurada; trocado por `.show()` não-modal.
- Eixo Y do popup ignorava a posição real do cursor, sempre abrindo perto do centro vertical do monitor.
- Anel do popup renderizava só 1 fatia (a favorita sob o cursor) em vez das 4, especificamente ao abrir o popup logo depois de interagir com a tela de Configurações. **Causa raiz real**: o próprio hotkey que abre o popup termina em Espaço (`Ctrl+Alt+Espaço`) - esse Espaço físico às vezes vaza pro popup recém-focado como um `keyPressEvent` normal, e o código tratava qualquer espaço digitado como início de busca, filtrando os favoritos pra só os que têm espaço no nome. Corrigido ignorando espaço como primeiro caractere do filtro. Três tentativas anteriores de "consertar composição do DWM" (raise+repaint, nudge de posição, hide+show) foram um beco sem saída - revertidas na mesma correção, não existia bug de composição nenhum.

## [0.1.1] - 2026-08-15

### Corrigido
- Paleta de cores do porte inicial tinha um acento ciano que não existe na identidade visual da GAIA - revertido pro acento dourado e pras cores originais do popup.
- Removido o toggle de automação de apps (kill-switch) herdado da GAIA - lá existe pra impedir a LLM de agir sozinha; não fazia sentido pro clique manual num favorito do IRIS, que já é sempre intencional.

## [0.1.0] - 2026-08-15

### Adicionado
- `iniciar_iris.bat` + `iniciar_iris_oculto.vbs` + `criar_atalho_desktop.vbs` (mesmo padrão de inicialização sem console do Project ARGUS).
