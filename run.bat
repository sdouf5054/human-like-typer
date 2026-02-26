@echo off
cd /d "%~dp0"
call micromamba activate human-like-typer
python main.py