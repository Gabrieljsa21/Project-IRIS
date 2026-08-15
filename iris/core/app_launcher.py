# -*- coding: utf-8 -*-
"""App launcher genérico - encontra e abre apps fixos, apps escaneados
(jogos da Steam + atalhos do Menu Iniciar, ver `apps_scanner.py`) e apps
manuais (caminho apontado à mão na tela de Configurações). Portado de
`Project G.A.I.A/assistant/features/app_launcher/app_launcher.py` (ver
`ARQUITETURA.md` na raiz do repo) - a versão original também processava tags
de voz/LLM (`<APP:abrir:...>`) e escrita ditada no Bloco de Notas, que são
features de PRODUTO da GAIA (não deste launcher) e ficaram de fora do porte."""

import os
import json
import logging
import subprocess

import psutil

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# Apps manuais - registro PRÓPRIO, separado do escaneamento automático
# (apps_scanner.py) de propósito: um app manual nunca deve ser removido só
# porque um reescaneamento não o encontrou nesse ciclo (ele não é
# "descoberto", foi apontado explicitamente pelo usuário).
ARQUIVO_APPS_MANUAIS = "data/apps_manuais.json"


def _carregar_apps_manuais():
    if not os.path.exists(ARQUIVO_APPS_MANUAIS):
        return {}
    try:
        with open(ARQUIVO_APPS_MANUAIS, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def _salvar_apps_manuais(dados):
    os.makedirs(os.path.dirname(ARQUIVO_APPS_MANUAIS), exist_ok=True)
    with open(ARQUIVO_APPS_MANUAIS, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)


def adicionar_app_manual(nome, caminho):
    dados = _carregar_apps_manuais()
    dados[nome.lower()] = {
        "target": caminho,
        "tipo": "manual",
        "aliases": [],
        "process_names": [os.path.basename(caminho)],
        "allow_multiple": True,
    }
    _salvar_apps_manuais(dados)


def remover_app_manual(nome):
    dados = _carregar_apps_manuais()
    dados.pop(nome.lower(), None)
    _salvar_apps_manuais(dados)


def listar_apps_manuais():
    return dict(_carregar_apps_manuais())


# Apps fixos - conhecidos desde sempre, sem depender de escaneamento nenhum.
# Extraído de dentro de `AppLauncher.__init__` pra constante de MÓDULO - o
# popup radial precisa listar todos os apps conhecidos (fixos + escaneados)
# pro usuário escolher favoritos, sem precisar instanciar `AppLauncher`.
APPS_FIXOS = {
    "bloco de notas": {
        "target": "notepad",
        "aliases": ["anotações", "notas", "editor de texto", "notepad", "escrever"],
        "process_names": ["notepad.exe"],
        "allow_multiple": True
    },
    "calculadora": {
        "target": "calc",
        "aliases": ["números", "cálculo", "calculadora", "contas", "calcular", "calculo"],
        "process_names": ["calculator.exe", "calc.exe", "CalculatorApp.exe"],
        "allow_multiple": True
    },
    "youtube": {
        "target": "https://www.youtube.com",
        "aliases": ["vídeos", "ver vídeo", "site do youtube", "youtube", "assistir algo"],
        "process_names": [],
        "allow_multiple": True
    },
    "navegador": {
        "target": "https://www.google.com",
        "aliases": ["google", "pesquisar", "web", "internet", "browser", "navegador", "chrome", "edge"],
        "process_names": ["chrome.exe", "msedge.exe", "firefox.exe", "opera.exe", "brave.exe"],
        "allow_multiple": True
    },
    "mixer de volume": {
        "target": "sndvol.exe",
        "aliases": ["mixer de som", "volume mixer", "mixer"],
        "process_names": ["sndvol.exe"],
        "allow_multiple": False
    },
    "som": {
        "target": "ms-settings:sound",
        "aliases": ["configurações de som", "sound settings", "áudio", "configuração de áudio"],
        # ms-settings: abre o processo "SystemSettings.exe" da UWP, não um
        # .exe com esse nome - deixar vazio evita avisar "pode não ter
        # instalado" só porque o nome do processo não bate.
        "process_names": [],
        "allow_multiple": True
    },
    "tela": {
        "target": "ms-settings:display",
        "aliases": ["configurações de tela", "display", "resolução de tela", "configuração de tela"],
        "process_names": [],
        "allow_multiple": True
    }
}


def listar_jogos_steam_instalados():
    """Só os jogos da Steam (`tipo == "steam_jogo"`) dentre os apps
    escaneados, em ordem alfabética - usado pela categoria "🎮 Steam" do popup
    radial. Lê o que já foi escaneado, não escaneia de novo sozinho."""
    from iris.core import apps_scanner
    apps = apps_scanner.carregar_apps_escaneados()
    return sorted(nome for nome, dados in apps.items() if dados.get("tipo") == "steam_jogo")


def obter_icones_jogos_steam():
    """{nome_jogo: caminho_do_icone} pra TODOS os jogos da Steam escaneados
    que têm ícone encontrado - usado pelo popup radial pra desenhar o ícone
    REAL do jogo (cache local da Steam) em vez de um emoji genérico."""
    from iris.core import apps_scanner
    apps = apps_scanner.carregar_apps_escaneados()
    return {
        nome: dados["icone"] for nome, dados in apps.items()
        if dados.get("tipo") == "steam_jogo" and dados.get("icone")
    }


def listar_nomes_apps_disponiveis():
    """Lista COMPLETA de apps conhecidos (fixos + escaneados + manuais), em
    ordem alfabética, sem precisar instanciar `AppLauncher` - usado pela tela
    de Configurações pra montar a lista de favoritos disponíveis."""
    from iris.core import apps_scanner
    apps = dict(APPS_FIXOS)
    apps.update(apps_scanner.carregar_apps_escaneados())
    apps.update(_carregar_apps_manuais())
    return sorted(apps.keys())


class AppLauncher:
    def __init__(self, output_callback=None):
        self.output_callback = output_callback
        self.enabled = True

        self.apps = dict(APPS_FIXOS)

        # Carrega o que já foi escaneado numa sessão anterior (jogos da Steam
        # + atalhos do Menu Iniciar) - não escaneia de novo sozinho, só
        # reaproveita o último resultado salvo.
        from iris.core import apps_scanner
        self._apps_scanner = apps_scanner
        self._mesclar_apps_escaneados(apps_scanner.carregar_apps_escaneados())
        # Apps manuais - nunca marcados "escaneado", por isso sobrevivem a
        # qualquer `_mesclar_apps_escaneados`/`escanear_apps()` sem precisar
        # ser "encontrados" de novo.
        self.apps.update(_carregar_apps_manuais())

    def _mesclar_apps_escaneados(self, apps_escaneados):
        """Substitui SÓ as entradas marcadas escaneado=True (nunca mexe nos
        apps fixos acima) pelo dicionário passado - usado tanto no
        carregamento inicial quanto depois de um `escanear_apps()` novo. Isso
        é o que faz um app desinstalado sumir da lista: ele simplesmente não
        vem mais em `apps_escaneados`."""
        for nome in [n for n, dados in self.apps.items() if dados.get("escaneado")]:
            del self.apps[nome]
        self.apps.update(apps_escaneados)

    def escanear_apps(self):
        """Reescaneia jogos da Steam + atalhos instalados agora, atualiza
        `self.apps` e devolve uma mensagem pronta (pt-BR) resumindo o que
        mudou."""
        resultado = self._apps_scanner.escanear_tudo()
        self._mesclar_apps_escaneados(resultado["apps"])

        partes = [
            f"Escaneei de novo: {resultado['total_jogos_steam']} jogo(s) da Steam e "
            f"{resultado['total_atalhos']} programa(s) do Menu Iniciar encontrados."
        ]
        if not resultado["steam_encontrada"]:
            partes.append("Não achei uma instalação da Steam nesse PC (contagem de jogos fica zerada).")
        if resultado["adicionados"]:
            partes.append(f"Novo(s) desde a última vez: {', '.join(resultado['adicionados'])}.")
        if resultado["removidos"]:
            partes.append(f"Não encontrado(s) mais (provavelmente desinstalado(s)): {', '.join(resultado['removidos'])}.")

        msg = "\n".join(partes)
        self.log(msg)
        return msg

    def log(self, message):
        if self.output_callback:
            self.output_callback(message)
        else:
            print(message)

    def find_app(self, command):
        if not command:
            return None, None
        command = command.lower().strip()

        for app_name, app_data in self.apps.items():
            if command == app_name.lower() or command in [a.lower() for a in app_data.get('aliases', [])]:
                return app_name, app_data['target']

        last_words = ' '.join(command.split()[-2:])
        for app_name, app_data in self.apps.items():
            if last_words in app_name.lower() or any(last_words in a.lower() for a in app_data.get('aliases', [])):
                return app_name, app_data['target']

        return None, None

    def is_app_running(self, app_name):
        if app_name not in self.apps:
            return False
        process_names = self.apps[app_name].get('process_names', [])
        if not process_names:
            return False

        for proc in psutil.process_iter(['name']):
            try:
                proc_name = proc.info['name'].lower()
                for target_name in process_names:
                    if target_name.lower() in proc_name:
                        return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return False

    def close_app(self, app_name):
        try:
            closed = False
            for proc in psutil.process_iter(['name']):
                try:
                    proc_name = proc.info['name'].lower()
                    for target_name in self.apps[app_name].get('process_names', []):
                        if target_name.lower() in proc_name:
                            proc.terminate()
                            closed = True
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            return closed
        except Exception as e:
            self.log(f"Erro ao fechar {app_name}: {e}")
            return False

    def open_app_cmd(self, app_name, target):
        try:
            # Aspas + título vazio pro "start" - necessário pros targets
            # escaneados (caminho de .exe/.lnk pode ter espaço), e continua
            # funcionando igual pros targets fixos (URL, "calc", "notepad").
            subprocess.Popen(f'start "" "{target}"', shell=True)
            return True
        except Exception as e:
            self.log(f"Erro ao abrir {app_name}: {str(e)}")
            return False
