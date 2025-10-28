# Checklist de Verificación de Entorno

Este checklist asegura que el entorno esté correctamente configurado para desarrollar agentes IA.

## Requisitos del Sistema

- [x] Hardware: CPU AMD Ryzen 5 7600X, RAM 32 GB, GPU NVIDIA GTX 1080 (4 GB VRAM)
- [x] SO: Windows con WSL2 Ubuntu instalado

## Software Instalado

- [x] Python 3.12.10 instalado y configurado
- [x] Git >= 2.51.1 instalado
- [x] VS Code >= 1.105.1 instalado
- [x] Ollama 0.12.6 instalado y corriendo (puerto 11434)

## Entorno Virtual

- [x] Venv `.venv` creado con Python 3.12
- [x] Dependencias instaladas desde `requirements.txt`:
  - [x] langchain
  - [x] openai
  - [x] crewai
  - [x] ollama-python
  - [x] python-dotenv

## Configuración

- [x] Archivo `.env` creado desde `.env.example` (configurar API keys)
- [x] Scripts disponibles: `scripts/setup.ps1`, `Makefile`
- [x] `.gitignore` configurado para excluir `.env`, `.venv`, logs

## Modelos IA

- [x] Ollama corriendo en background
- [x] Modelo `llama2:latest` descargado (3.8 GB)
- [x] GPU NVIDIA detectada y configurada para CUDA

## Verificación Final

- [ ] Ejecutar `python -c "import langchain, crewai; print('OK')"`
- [ ] Probar conexión a Ollama: `ollama list`
- [ ] Configurar API keys en `.env`
- [ ] Ejecutar setup: `.\scripts\setup.ps1`

## Notas para Nuevos Miembros

1. Clona el repositorio: `git clone <url>`
2. Ejecuta setup: `.\scripts\setup.ps1`
3. Copia `.env.example` a `.env` y configura tus claves API
4. Activa venv: `& .venv\Scripts\Activate.ps1`
5. Verifica: `python -c "import crewai; print('Listo')"`

Última actualización: 28 de octubre de 2025
