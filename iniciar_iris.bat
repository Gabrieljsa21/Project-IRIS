@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8

rem Versao "sem console" - o IRIS roda em segundo plano (pythonw), sem janela de
rem terminal nenhuma. O popup radial nao tem borda nem "X" de proposito -
rem pra fechar o IRIS, clique com o botao direito no icone dele na bandeja do sistema.

start "" /B ".venv\Scripts\pythonw.exe" -m iris.main
