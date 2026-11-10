# -*- coding: utf-8 -*-
"""Caminhos e leitura/gravação de JSON compartilhados pelo core.

- Caminhos ancorados na RAIZ do repositório (não no diretório de onde o
  processo foi iniciado): rodar `iris` de outra pasta usa os mesmos dados.
- Gravação atômica (arquivo temporário + `os.replace`): uma queda no meio da
  escrita nunca deixa o JSON pela metade.
- Leitura que distingue "não existe" de "existe e está ilegível": quem chama
  decide o que fazer com um arquivo corrompido, em vez de tratar como vazio e
  gravar o padrão por cima."""

import json
import os
import shutil
import time

RAIZ_PROJETO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PASTA_DADOS = os.path.join(RAIZ_PROJETO, "data")


class ArquivoIlegivel(Exception):
    """O arquivo existe, mas não pôde ser lido como JSON."""


def caminho_dados(nome_arquivo):
    return os.path.join(PASTA_DADOS, nome_arquivo)


def resolver_caminho(caminho):
    """Caminho relativo (formato salvo nos JSONs, ex.: `assets/icones_
    customizados/x.png`) vira absoluto a partir da raiz do projeto; absoluto
    passa direto."""
    if not caminho or os.path.isabs(caminho):
        return caminho
    return os.path.join(RAIZ_PROJETO, caminho)


def ler_json(caminho):
    """Devolve o conteúdo, ou None se o arquivo não existir. Levanta
    `ArquivoIlegivel` se existir e não for um JSON válido."""
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return None
    except (OSError, ValueError) as erro:
        raise ArquivoIlegivel(f"{caminho}: {erro}") from erro


def ler_json_ou(caminho, padrao):
    """Para arquivos reconstruíveis (ex.: resultado de escaneamento):
    ausente ou ilegível devolve `padrao`."""
    try:
        dados = ler_json(caminho)
    except ArquivoIlegivel:
        return padrao
    return padrao if dados is None else dados


def gravar_json_atomico(caminho, dados, manter_backup=False):
    """Grava em `<caminho>.tmp` e troca pelo definitivo numa operação só.
    Com `manter_backup`, a versão anterior fica em `<caminho>.bak`."""
    pasta = os.path.dirname(caminho)
    if pasta:
        os.makedirs(pasta, exist_ok=True)
    temporario = caminho + ".tmp"
    with open(temporario, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    if manter_backup and os.path.exists(caminho):
        try:
            shutil.copyfile(caminho, caminho + ".bak")
        except OSError:
            pass
    os.replace(temporario, caminho)


def separar_arquivo_ilegivel(caminho):
    """Renomeia um arquivo corrompido para `<caminho>.corrompido-<data>` em
    vez de apagar ou sobrescrever. Devolve o novo caminho (ou None)."""
    destino = f"{caminho}.corrompido-{time.strftime('%Y%m%d-%H%M%S')}"
    try:
        os.replace(caminho, destino)
        return destino
    except OSError:
        return None
