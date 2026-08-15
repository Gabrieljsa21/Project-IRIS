# -*- coding: utf-8 -*-
"""Monitoramento de uso de hardware (CPU/RAM/GPU) - métricas do sistema em
tempo real, usadas pelo mostrador decorativo no centro do popup radial.
Portado, sem nenhuma alteração de comportamento, de `Project G.A.I.A/
assistant/features/hardware_monitor/hardware_monitor.py` (ver
`ARQUITETURA.md` na raiz do repo).

GPU via `nvidia-smi` (subprocess, sem dependência nova de pip - já vem com o
driver da NVIDIA). Sem NVIDIA/nvidia-smi fora do PATH, a métrica de GPU vira
None - CPU/RAM continuam funcionando normalmente via psutil."""

import subprocess

import psutil


def obter_metricas_sistema():
    """CPU/RAM/GPU do sistema como um todo, 0-100 cada (GPU None se não disponível)."""
    return {
        "cpu_percent": psutil.cpu_percent(interval=None),
        "ram_percent": psutil.virtual_memory().percent,
        "gpu_percent": obter_uso_gpu(),
    }


def obter_uso_gpu():
    try:
        resultado = subprocess.run(
            ["nvidia-smi", "--query-gpu=utilization.gpu", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5,
        )
        if resultado.returncode != 0:
            return None
        return float(resultado.stdout.strip().splitlines()[0])
    except Exception:
        return None
