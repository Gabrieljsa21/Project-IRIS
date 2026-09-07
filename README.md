<p align="center">
  <img src="assets/logo_iris.png" alt="Iris" width="180">
</p>

# Project IRIS

Menu radial para Windows que abre programas, pastas, sites, atalhos e jogos da Steam com uma tecla global.

## Recursos principais

- menu circular aberto por `Ctrl+Alt+Espaço`;
- favoritos e categorias editáveis;
- busca de programas e jogos instalados;
- suporte a várias páginas e níveis;
- ícone na bandeja;
- sistema de plugins opcionais.

## Origem do nome

IRIS vem de Íris (Ἶρις), deusa grega do arco-íris e mensageira dos deuses. Na mitologia, ela transporta mensagens entre diferentes lugares e entidades. O arco-íris representa seu caminho e funciona como uma ponte entre o céu e a terra.

Essa origem combina com o projeto como meio de navegação e acesso: **Íris → mensageira e ponte → interface → acesso a diferentes funções**. O nome também se liga à íris do olho. Seu formato radial lembra a organização do menu, com o usuário no centro e diferentes caminhos ao redor.

### Identidade visual

A logo mostra Íris como uma figura feminina alada. O espectro de cores faz parte das próprias asas, que formam quase um círculo e lembram caminhos se abrindo em várias direções.

É a logo mais colorida do conjunto, o que facilita seu reconhecimento em tamanho pequeno. A composição transforma arco-íris, movimento e asas em uma ponte visual entre o usuário e os sistemas.

## Requisitos

- Windows;
- Python 3.11 ou mais recente.

## Instalação e uso

```powershell
uv venv
uv pip install -e .
python -m iris.main
```

Na primeira execução, o IRIS cria `data/menu_radial_config.json`. Use o ícone da bandeja para abrir as configurações. `iniciar_iris_oculto.vbs` inicia o menu sem terminal visível.

## Integrações com outros projetos

- **GAIA:** o plugin `iris_plugin_gaia` adiciona atalhos para o avatar, funções da assistente e ações do VTube Studio.
- **MOIRAI:** o plugin `iris_plugin_moirai` adiciona a categoria Watchlist e acesso rápido aos animes acompanhados.
- **Projetos do ecossistema:** a categoria Projects abre os inicializadores com os ícones oficiais quando eles estão instalados.

Todas as integrações são opcionais. O menu principal funciona sozinho.

## Documentação

- [Arquitetura](docs/ARQUITETURA.md)
- [Pendências](docs/TODO.md)
- [Versionamento](docs/VERSIONAMENTO_CHANGELOG.md)
- [Plugin da GAIA](plugins/iris_plugin_gaia/README.md)
- [Plugin do MOIRAI](plugins/iris_plugin_moirai/README.md)
- [Histórico de versões](CHANGELOG.md)
- [Padrão de documentação](docs/PADRAO_DOCUMENTACAO.md)

## Situação atual

O menu, as configurações, o início sem terminal e os plugins opcionais estão em uso.
