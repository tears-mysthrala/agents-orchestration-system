# Sistema de Orquestación de Agentes IA

[![GitHub Repository](https://img.shields.io/badge/GitHub-agents--orchestration--system-blue?logo=github)](https://github.com/tears-mysthrala/agents-orchestration-system)
[![Python](https://img.shields.io/badge/Python-3.12+-blue?logo=python)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![Version](https://img.shields.io/badge/Version-2025.10.28-orange)](https://github.com/tears-mysthrala/agents-orchestration-system/releases/tag/2025.10.28)

## Creation of agents for simultaneous development

### Vision general

Proyecto para definir, construir y operar agentes de desarrollo que trabajen en paralelo, con soporte para modelos locales mediante Ollama y compatibilidad con frameworks del curso "AI Agents for Beginners" de Microsoft.

### Objetivos clave

- Entorno reproducible para ejecutar agentes coordinados en tareas de desarrollo de software.
- Integracion con modelos locales (Ollama) y remotos (GitHub Models, Azure AI Foundry) segun sea necesario.
- Documentacion modular que permita a cualquier contribuidor entender responsabilidades, dependencias y plan de entrega.

### Estructura documental

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
- `scripts/run_web.py`: script para ejecutar la interfaz web de control y monitoreo.
- `web/`: módulo con la API FastAPI y interfaz web para gestionar agentes.
- `docs/operations/playbook.md`: respuesta operativa y escalamiento.

### Hoja de ruta resumida

| Fase | Duracion estimada | Resultado principal |
| --- | --- | --- |
| Preparacion | Semana 1 | Entorno local y remoto listo, modelos descargados, configuracion de secretos definida |
| Desarrollo de agentes | Semanas 2-3 | Agentes especializados implementados y probados individualmente |
| Orquestacion | Semana 4 | Pipeline de ejecucion paralela con monitoreo basico |
| Calidad y operacion | Semana 5 | Pruebas end-to-end, politicas de seguridad y playbooks operativos |

### Requisitos recomendados

- **Hardware**: CPU multinucleo, 16 GB de RAM como minimo (32 GB si ejecutaras varios modelos en paralelo) y GPU con al menos 8 GB de VRAM si quieres acelerar inferencias.
- **Sistema operativo**: Windows 11 actualizado con soporte para WSL2 o Ubuntu/macOS equivalente para reducir friccion con dependencias de IA.
- **Almacenamiento**: 40 GB libres para repositorios, entornos virtuales y descargas de modelos locales.

### Dependencias de software base

- **Git** >= 2.25 con soporte para `partial clone` y `sparse-checkout`, segun la guia oficial: `winget install --id Git.Git -e --source winget`.
- **Python** 3.12 (requerido por los notebooks del curso de Microsoft). Verifica con `python --version` y crea un entorno virtual con `python -m venv .venv`.
- **pip** actualizado dentro del entorno virtual: `python -m pip install --upgrade pip`.
- **Visual Studio Code** con las extensiones Python, Jupyter y GitHub Copilot para trabajar sobre los cuadernos del repositorio.
- **Make** o alternativas (PowerShell scripts) si vas a automatizar ejecucion de agentes.

### Dependencias del curso de Microsoft

- Clona o haz fork de `microsoft/ai-agents-for-beginners` siguiendo la leccion de Course Setup: [guia oficial](https://github.com/microsoft/ai-agents-for-beginners/tree/main/00-course-setup).
- Instala las librerias Python del curso desde el `requirements.txt` oficial: `pip install -r requirements.txt`.
- Copia `.env.example` a `.env` y rellena las variables (por ejemplo `GITHUB_TOKEN` para GitHub Models o credenciales de Azure AI Agent Service si las empleas).
- Configura tokens o credenciales siguiendo el principio de minimo privilegio; el curso detalla los permisos necesarios para GitHub Models y Azure.

### Modelos locales con Ollama

- Instala Ollama desde [ollama.com](https://ollama.com/download) y verifica con `ollama run llama3 "Hello"`.
- Descarga los modelos que vayas a usar en paralelo (por ejemplo `ollama pull llama3` o `ollama pull mistral`). Considera el tamano para evitar saturar RAM/VRAM.
- Expone Ollama como servicio local (`ollama serve`) y documenta el puerto (por defecto `11434`) para que los agentes puedan conectarse.
- Define variables de entorno (ej. `OLLAMA_HOST=http://localhost:11434`) en tu `.env` o en la configuracion de cada agente.

### Gestion de multiples agentes en paralelo

- Usa orquestadores compatibles (Semantic Kernel, AutoGen, Microsoft Agent Framework) incluidos en el curso; crea procesos o threads separados por agente para evitar bloqueos.
- Apoyate en colas de tareas (Redis, RabbitMQ) si los agentes comparten recursos y necesitan coordinacion.
- Implementa un archivo de configuracion central (`agents.config.json` o similar) para registrar capacidades, llaves y modelos asignados a cada agente.
- Define scripts de supervision (por ejemplo, `invoke`, `nox` o `tox`) que permitan lanzar todos los agentes y monitorear logs en paralelo.
- Anade pruebas unitarias/integracion para cada agente antes de ejecutarlos simultaneamente y garantizar que no comparten estado mutable inesperado.

### Buenas practicas adicionales

- Versiona solo plantillas de `.env` y gestiona secretos con GitHub Encrypted Secrets o Azure Key Vault cuando despliegues fuera de local.
- Automatiza la configuracion inicial con scripts (`setup.ps1`, `Makefile`) que creen entornos, instalen dependencias y descarguen modelos.
- Documenta en este README las combinaciones de modelos probadas, consumo de recursos y cualquier ajuste especifico (por ejemplo, limites de tokens o planificacion de tareas).
- Monitoriza uso de hardware con herramientas como `htop`, `nvidia-smi` o el Monitor de recursos de Windows para detectar cuellos de botella al correr agentes en paralelo.

### Interfaz Web

El proyecto incluye una interfaz web para controlar y monitorizar los agentes de forma interactiva.

#### Inicio Rápido

```bash
# Activar entorno virtual e instalar dependencias
.venv\Scripts\Activate.ps1  # Windows
source .venv/bin/activate    # Linux/Mac
pip install -r requirements.txt

# Ejecutar el servidor web
uvicorn web.app:app --reload --host 0.0.0.0 --port 8000

# O usar el script proporcionado
python scripts/run_web.py
```

#### Acceso

- **API Principal**: `http://127.0.0.1:8000`
- **Dashboard en Tiempo Real**: `http://127.0.0.1:8000/static/dashboard.html`
- **Documentación API**: `http://127.0.0.1:8000/docs`
- **Interfaz Original**: `http://127.0.0.1:8000/static/index.html`

#### Dashboard en Tiempo Real (Nuevo)

El nuevo dashboard proporciona monitoreo en tiempo real de los agentes mediante WebSocket:

- **Métricas en vivo**: Agentes totales, activos, tareas pendientes y completadas
- **Tabla de agentes**: Estado actual, tareas asignadas, métricas de rendimiento
- **Control de agentes**: Botones para pausar, reanudar, detener y reiniciar agentes
- **Logs en vivo**: Stream de eventos y logs de los agentes en tiempo real
- **Actualizaciones automáticas**: La interfaz se actualiza automáticamente vía WebSocket

![Dashboard Screenshot](https://github.com/user-attachments/assets/7400abde-083e-41a2-b69a-e808ca1eff36)

#### API REST y WebSocket

**Endpoints principales:**

- `GET /health` - Health check del servicio
- `GET /metrics` - Métricas básicas del sistema
- `GET /api/agents` - Lista de agentes con estado en tiempo real
- `GET /api/agents/{agent_id}` - Detalle de un agente específico
- `POST /api/agents/{agent_id}/action` - Ejecutar acciones (pause, resume, stop, restart, prioritize)
- `WS /api/agents/ws` - WebSocket para actualizaciones en tiempo real

**Acciones disponibles:**
- `pause` - Pausar un agente en ejecución
- `resume` - Reanudar un agente pausado
- `stop` - Detener un agente
- `restart` - Reiniciar un agente
- `prioritize` - Establecer prioridad de un agente

**Documentación completa**: Ver [web/README.md](web/README.md) para ejemplos de uso, testing con curl/wscat, y guía de producción.

La interfaz utiliza FastAPI para el backend, WebSocket para comunicación en tiempo real, y una interfaz HTML/JS reactiva para el frontend.

### Buenas prácticas adicionales

## 🤝 Cómo contribuir

¡Las contribuciones son bienvenidas! Este proyecto sigue un flujo de trabajo distribuido con desarrollo paralelo.

### Configuración inicial

1. **Clona el repositorio:**

   ```bash
   git clone https://github.com/tears-mysthrala/agents-orchestration-system.git
   cd agents-orchestration-system
   ```

2. **Configura el entorno:**

   ```bash
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   pip install -r requirements.txt
   ```

3. **Verifica la instalación:**

   ```bash
   invoke --list  # Lista todas las tareas disponibles
   invoke run-parallel  # Prueba la ejecución paralela
   ```

### Flujo de desarrollo

1. **Crea una rama** para tu feature/bugfix:

   ```bash
   git checkout -b feature/nueva-funcionalidad
   ```

2. **Sigue el roadmap** documentado en `docs/roadmap.md`

3. **Ejecuta tests** antes de commitear:

   ```bash
   invoke test
   ```

4. **Commit con mensajes descriptivos** siguiendo conventional commits

5. **Push y crea un Pull Request** con descripción detallada

### Estructura del proyecto

- `agents/` - Implementaciones de agentes individuales
- `orchestration/` - Sistema de coordinación y workflows
- `config/` - Configuraciones centralizadas
- `docs/` - Documentación completa
- `tests/` - Suite de pruebas
- `scripts/` - Automatización y utilidades

### Reportar issues

Usa los [GitHub Issues](https://github.com/tears-mysthrala/agents-orchestration-system/issues) para:

- Reportar bugs
- Solicitar nuevas funcionalidades
- Preguntas sobre la arquitectura

### Licencia

Este proyecto está bajo la Licencia MIT - ver el archivo [LICENSE](LICENSE) para más detalles.

## 🏷️ Versionado

Este proyecto usa **versionado por fecha** (formato `YYYY.MM.DD`) para mejor mantenibilidad en desarrollo activo, en lugar del versionado semántico tradicional.

- **Última versión**: `2025.10.28`
- **Cambios principales**: Sistema de orquestación core con logging estructurado
