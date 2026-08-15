# -*- coding: utf-8 -*-
"""Escaneia jogos da Steam instalados e atalhos do Menu Iniciar, e devolve um
dicionário no mesmo formato que `AppLauncher.apps` espera (target/aliases/
process_names) - ver `_mesclar_apps_escaneados` em `app_launcher.py`, que
injeta o resultado disso no dicionário principal marcado com
"escaneado": True.

Cada chamada de `escanear_tudo()` é uma fotografia completa do estado atual
(não um incremento) - por isso desinstalar um jogo/programa simplesmente o
tira do resultado, sem precisar de nenhuma lógica extra de remoção."""

import os
import re
import glob
import json
import winreg

ARQUIVO_ESCANEADOS = "data/apps_escaneados.json"

# Filtro best-effort pra atalhos que não são "o programa em si" (desinstalador,
# licença, site de suporte) - a Steam não tem esse problema (appmanifest só
# lista jogos de verdade), mas o Menu Iniciar mistura tudo no mesmo lugar.
_RUIDO_NOME_ATALHO = [
    "uninstall", "desinstal", "unins000", "read me", "readme", "leia-me", "leiame",
    "license", "licença", "licenca", "eula", "help", "ajuda", "faq", "changelog",
    "website", "site oficial", "support", "suporte", "documentation", "documentação",
    "documentacao", "update", "atualizar", "atualização", "atualizacao",
]


def _steam_install_path():
    """Acha a pasta de instalação da Steam via registro - None se não estiver instalada."""
    chaves = [
        (winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam", "SteamPath"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam", "InstallPath"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Valve\Steam", "InstallPath"),
    ]
    for raiz, subchave, valor in chaves:
        try:
            with winreg.OpenKey(raiz, subchave) as chave:
                caminho, _ = winreg.QueryValueEx(chave, valor)
                if caminho and os.path.isdir(caminho):
                    return os.path.normpath(caminho)
        except OSError:
            continue
    return None


def _bibliotecas_steam(caminho_steam):
    """Devolve a lista de pastas "steamapps" de TODAS as bibliotecas (a
    instalação principal + qualquer HD/SSD extra configurado), lendo
    libraryfolders.vdf."""
    bibliotecas = {os.path.join(caminho_steam, "steamapps")}

    vdf_path = os.path.join(caminho_steam, "steamapps", "libraryfolders.vdf")
    if os.path.isfile(vdf_path):
        try:
            with open(vdf_path, "r", encoding="utf-8", errors="ignore") as f:
                conteudo = f.read()
            for caminho_bruto in re.findall(r'"path"\s*"([^"]+)"', conteudo):
                caminho_normalizado = caminho_bruto.replace("\\\\", "\\")
                pasta = os.path.join(caminho_normalizado, "steamapps")
                if os.path.isdir(pasta):
                    bibliotecas.add(pasta)
        except OSError:
            pass

    return [b for b in bibliotecas if os.path.isdir(b)]


_ARQUIVOS_ARTE_GRANDE_STEAM = {
    "library_600x900.jpg", "library_header.jpg", "library_hero.jpg",
    "library_hero_blur.jpg", "logo.png", "header.jpg", "assetcache.vdf",
}


def _icone_jogo_steam(caminho_steam, appid):
    """Acha o ícone pequeno (quadrado) de um jogo no cache local da Steam
    (`appcache/librarycache/<appid>/`). A pasta de cada appid tem várias
    imagens (capa vertical, banner, hero, logo) + o ícone de verdade num
    arquivo de nome HASH (imprevisível, muda por jogo) - o ícone é sempre o
    MENOR arquivo da pasta (1-2KB, contra dezenas/centenas de KB das artes
    grandes) - heurística por tamanho em vez de tentar adivinhar o nome do
    arquivo, robusta a mudanças de versão da Steam. Devolve None se a pasta
    não existir ou não tiver nada."""
    pasta = os.path.join(caminho_steam, "appcache", "librarycache", str(appid))
    if not os.path.isdir(pasta):
        return None
    try:
        candidatos = [
            os.path.join(pasta, nome) for nome in os.listdir(pasta)
            if nome not in _ARQUIVOS_ARTE_GRANDE_STEAM and os.path.isfile(os.path.join(pasta, nome))
        ]
    except OSError:
        return None
    if not candidatos:
        return None
    return min(candidatos, key=os.path.getsize)


def escanear_jogos_steam():
    """Devolve {nome_do_jogo_lower: {target, tipo, appid, icone}} lendo os
    appmanifest_*.acf de cada biblioteca. target é o protocolo oficial
    steam://rungameid/<appid> - a própria Steam trata (inclusive abrindo o
    cliente se estiver fechado)."""
    caminho_steam = _steam_install_path()
    if not caminho_steam:
        return {}

    jogos = {}
    for pasta_steamapps in _bibliotecas_steam(caminho_steam):
        for acf_path in glob.glob(os.path.join(pasta_steamapps, "appmanifest_*.acf")):
            try:
                with open(acf_path, "r", encoding="utf-8", errors="ignore") as f:
                    conteudo = f.read()
                appid_match = re.search(r'"appid"\s*"(\d+)"', conteudo)
                nome_match = re.search(r'"name"\s*"([^"]+)"', conteudo)
                if not appid_match or not nome_match:
                    continue
                appid = appid_match.group(1)
                nome = nome_match.group(1).strip()
                if not nome:
                    continue
                jogos[nome.lower()] = {
                    "target": f"steam://rungameid/{appid}",
                    "tipo": "steam_jogo",
                    "appid": appid,
                    "icone": _icone_jogo_steam(caminho_steam, appid),
                    "aliases": [],
                    "process_names": [],
                    "allow_multiple": False,
                    "escaneado": True,
                }
            except OSError:
                continue

    return jogos


def _nome_atalho_e_ruido(nome_lower):
    return any(ruido in nome_lower for ruido in _RUIDO_NOME_ATALHO)


def _resolver_atalho(shell, lnk_path):
    """Lê o .lnk e devolve o caminho real do executável apontado, ou None se
    não conseguir resolver (atalho quebrado, aponta pra pasta, etc)."""
    try:
        atalho = shell.CreateShortCut(lnk_path)
        alvo = atalho.Targetpath
        if alvo and os.path.isfile(alvo):
            return os.path.normpath(alvo)
    except Exception:
        pass
    return None


def escanear_atalhos_instalados():
    """Devolve {nome_do_programa_lower: {target, tipo, process_names}} lendo os
    .lnk do Menu Iniciar (todos os usuários + usuário atual). target é o .exe
    resolvido do atalho quando dá pra achar - cai pro próprio .lnk se não
    resolver."""
    import win32com.client

    pastas = [
        os.path.join(os.environ.get("PROGRAMDATA", ""), r"Microsoft\Windows\Start Menu\Programs"),
        os.path.join(os.environ.get("APPDATA", ""), r"Microsoft\Windows\Start Menu\Programs"),
    ]

    shell = win32com.client.Dispatch("WScript.Shell")
    programas = {}

    for pasta in pastas:
        if not pasta or not os.path.isdir(pasta):
            continue
        for lnk_path in glob.glob(os.path.join(pasta, "**", "*.lnk"), recursive=True):
            nome = os.path.splitext(os.path.basename(lnk_path))[0].strip()
            nome_lower = nome.lower()
            if not nome or _nome_atalho_e_ruido(nome_lower) or nome_lower in programas:
                continue

            exe_resolvido = _resolver_atalho(shell, lnk_path)
            programas[nome_lower] = {
                "target": exe_resolvido or lnk_path,
                "tipo": "atalho",
                "aliases": [],
                "process_names": [os.path.basename(exe_resolvido)] if exe_resolvido else [],
                "allow_multiple": True,
                "escaneado": True,
            }

    return programas


def _carregar_json():
    if not os.path.exists(ARQUIVO_ESCANEADOS):
        return {}
    try:
        with open(ARQUIVO_ESCANEADOS, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def _salvar_json(dados):
    os.makedirs(os.path.dirname(ARQUIVO_ESCANEADOS), exist_ok=True)
    with open(ARQUIVO_ESCANEADOS, "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=2, ensure_ascii=False)


def escanear_tudo():
    """Escaneia jogos da Steam + atalhos instalados, salva o resultado e
    devolve um resumo (adicionados/removidos/totais). Cada chamada é uma
    fotografia nova e completa - o que não foi encontrado dessa vez
    (desinstalado) simplesmente não entra no resultado salvo."""
    anterior = _carregar_json()

    jogos = escanear_jogos_steam()
    atalhos = escanear_atalhos_instalados()
    atual = {**jogos, **atalhos}

    adicionados = sorted(set(atual) - set(anterior))
    removidos = sorted(set(anterior) - set(atual))

    _salvar_json(atual)

    return {
        "apps": atual,
        "adicionados": adicionados,
        "removidos": removidos,
        "total_jogos_steam": len(jogos),
        "total_atalhos": len(atalhos),
        "steam_encontrada": bool(_steam_install_path()),
    }


def carregar_apps_escaneados():
    """Só lê o que já foi salvo da última vez (sem escanear de novo) - usado
    no início do processo pra não perder a lista entre reinícios."""
    return _carregar_json()
