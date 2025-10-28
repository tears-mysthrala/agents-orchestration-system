# Creation of agents for simultaneous development

## Vision general

Proyecto para definir, construir y operar agentes de desarrollo que trabajen en paralelo, con soporte para modelos locales mediante Ollama y compatibilidad con frameworks del curso "AI Agents for Beginners" de Microsoft.

## Objetivos clave

- Entorno reproducible para ejecutar agentes coordinados en tareas de desarrollo de software.
- Integracion con modelos locales (Ollama) y remotos (GitHub Models, Azure AI Foundry) segun sea necesario.
- Documentacion modular que permita a cualquier contribuidor entender responsabilidades, dependencias y plan de entrega.

## Estructura documental

- `docs/project-overview.md`: alcance, entregables, riesgos y gestion del proyecto.
- `docs/tasks/01-foundation.md`: backlog de tareas para preparar infraestructura y herramientas.
- `docs/tasks/02-agent-development.md`: actividades para disenar y construir agentes individuales.
- `docs/tasks/03-orchestration-and-automation.md`: tareas para coordinacion, despliegue y observabilidad.
- `docs/tasks/04-quality-and-ops.md`: pruebas, seguridad, compliance y operaciones.
- `.instructions`: pautas para el equipo humano involucrado en la construccion y mantenimiento.
- `.prompt`: contexto que consumiran los agentes para alinearse con la vision del proyecto.
- `config/agents.config.json`: plantilla de configuracion comun para agentes y modelos.
- `scripts/setup.ps1`: aprovisiona dependencias y entorno virtual.
- `scripts/run-agents.ps1`: ejemplo de orquestacion basica para lanzar agentes definidos en la configuracion.
- `docs/operations/playbook.md`: respuesta operativa y escalamiento.

## Hoja de ruta resumida

| Fase | Duracion estimada | Resultado principal |
| --- | --- | --- |
| Preparacion | Semana 1 | Entorno local y remoto listo, modelos descargados, configuracion de secretos definida |
| Desarrollo de agentes | Semanas 2-3 | Agentes especializados implementados y probados individualmente |
| Orquestacion | Semana 4 | Pipeline de ejecucion paralela con monitoreo basico |
| Calidad y operacion | Semana 5 | Pruebas end-to-end, politicas de seguridad y playbooks operativos |

## Requisitos recomendados

- **Hardware**: CPU multinucleo, 16 GB de RAM como minimo (32 GB si ejecutaras varios modelos en paralelo) y GPU con al menos 8 GB de VRAM si quieres acelerar inferencias.
- **Sistema operativo**: Windows 11 actualizado con soporte para WSL2 o Ubuntu/macOS equivalente para reducir friccion con dependencias de IA.
- **Almacenamiento**: 40 GB libres para repositorios, entornos virtuales y descargas de modelos locales.

## Dependencias de software base

- **Git** >= 2.25 con soporte para `partial clone` y `sparse-checkout`, segun la guia oficial: `winget install --id Git.Git -e --source winget`.
- **Python** 3.12 (requerido por los notebooks del curso de Microsoft). Verifica con `python --version` y crea un entorno virtual con `python -m venv .venv`.
- **pip** actualizado dentro del entorno virtual: `python -m pip install --upgrade pip`.
- **Visual Studio Code** con las extensiones Python, Jupyter y GitHub Copilot para trabajar sobre los cuadernos del repositorio.
- **Make** o alternativas (PowerShell scripts) si vas a automatizar ejecucion de agentes.

## Dependencias del curso de Microsoft

- Clona o haz fork de `microsoft/ai-agents-for-beginners` siguiendo la leccion de Course Setup: [guia oficial](https://github.com/microsoft/ai-agents-for-beginners/tree/main/00-course-setup).
- Instala las librerias Python del curso desde el `requirements.txt` oficial: `pip install -r requirements.txt`.
- Copia `.env.example` a `.env` y rellena las variables (por ejemplo `GITHUB_TOKEN` para GitHub Models o credenciales de Azure AI Agent Service si las empleas).
- Configura tokens o credenciales siguiendo el principio de minimo privilegio; el curso detalla los permisos necesarios para GitHub Models y Azure.

## Modelos locales con Ollama

- Instala Ollama desde [ollama.com](https://ollama.com/download) y verifica con `ollama run llama3 "Hello"`.
- Descarga los modelos que vayas a usar en paralelo (por ejemplo `ollama pull llama3` o `ollama pull mistral`). Considera el tamano para evitar saturar RAM/VRAM.
- Expone Ollama como servicio local (`ollama serve`) y documenta el puerto (por defecto `11434`) para que los agentes puedan conectarse.
- Define variables de entorno (ej. `OLLAMA_HOST=http://localhost:11434`) en tu `.env` o en la configuracion de cada agente.

## Gestion de multiples agentes en paralelo

- Usa orquestadores compatibles (Semantic Kernel, AutoGen, Microsoft Agent Framework) incluidos en el curso; crea procesos o threads separados por agente para evitar bloqueos.
- Apoyate en colas de tareas (Redis, RabbitMQ) si los agentes comparten recursos y necesitan coordinacion.
- Implementa un archivo de configuracion central (`agents.config.json` o similar) para registrar capacidades, llaves y modelos asignados a cada agente.
- Define scripts de supervision (por ejemplo, `invoke`, `nox` o `tox`) que permitan lanzar todos los agentes y monitorear logs en paralelo.
- Anade pruebas unitarias/integracion para cada agente antes de ejecutarlos simultaneamente y garantizar que no comparten estado mutable inesperado.

## Buenas practicas adicionales

- Versiona solo plantillas de `.env` y gestiona secretos con GitHub Encrypted Secrets o Azure Key Vault cuando despliegues fuera de local.
- Automatiza la configuracion inicial con scripts (`setup.ps1`, `Makefile`) que creen entornos, instalen dependencias y descarguen modelos.
- Documenta en este README las combinaciones de modelos probadas, consumo de recursos y cualquier ajuste especifico (por ejemplo, limites de tokens o planificacion de tareas).
- Monitoriza uso de hardware con herramientas como `htop`, `nvidia-smi` o el Monitor de recursos de Windows para detectar cuellos de botella al correr agentes en paralelo.
