<p align="center">
  <img src="assets/logo_iris.png" alt="Iris" width="180">
</p>

# Project-IRIS

Launcher radial pra Windows - um popup circular, acionado por um hotkey
global, pra abrir apps, pastas, sites, atalhos e jogos da Steam sem tirar as
mãos do teclado. Funciona 100% sozinho (nenhuma dependência externa além do
que está em `pyproject.toml`); quem também usa a [GAIA](../Project%20G.A.I.A)
(assistente pessoal do mesmo autor) pode instalar um plugin opcional que soma
categorias extras ao popup quando ela estiver rodando.

Arquitetura completa e decisões de design em [`ARQUITETURA.md`](ARQUITETURA.md).

## A origem de IRIS

O nome possui dois significados ligados ao projeto.

Na mitologia grega, Íris é a mensageira dos deuses e representa a conexão entre diferentes lugares.

Além disso, a íris do olho possui uma estrutura naturalmente radial, semelhante à organização do menu.

O nome representa, portanto, um ponto central que conecta o usuário aos seus aplicativos, pastas, ações e atalhos.

## Uso standalone

```bash
uv venv
uv pip install -e .
python -m iris.main
```

`Ctrl+Alt+Espaço` abre o popup (2º toque fecha). Um ícone fica na bandeja do
sistema com acesso a **Configurações** (favoritos, categorias, pastas, jogos
da Steam, preferências) e **Sair** - não existe janela principal nem entrada
na barra de tarefas, só o popup e a bandeja.

Na primeira execução, `data/menu_radial_config.json` é criado sozinho com um
punhado de favoritos padrão (bloco de notas, calculadora, YouTube,
navegador) - ajuste tudo pela tela de Configurações. `data/
menu_radial_config.example.json` mostra o schema completo preenchido (sem
nenhum dado pessoal real).

## Plugin opcional da GAIA

Quem também roda a [GAIA](../Project%20G.A.I.A) pode instalar
`plugins/iris_plugin_gaia/` pelo botão "Instalar integração com a GAIA"
(Configurações → Preferências → Plugins) - ou manualmente
(`uv pip install -e plugins/iris_plugin_gaia`) - pra ganhar categorias
extras no popup quando ela estiver de pé. Hoje só **Avatar (Overlay)** está
funcional de verdade (reaproveita a API HTTP já existente da GAIA);
**Funções da Gaia**, **Animações do VTube Studio** e **Anime Tracker** são
stubs documentados em `plugins/iris_plugin_gaia/TODO.md`, pendentes de um
endpoint/IPC que ainda não existe do lado da GAIA.

## Estado atual

Extração inicial do Menu Radial que já existia dentro da GAIA (ver
`ARQUITETURA.md`, seção "Estado atual") - popup, persistência, app launcher
genérico e monitor de hardware portados e funcionais; tela de Configurações
própria criada do zero (a GAIA nunca teve uma standalone, sempre dependeu do
Painel dela). Ver `TODO.md` pras pendências reais.
