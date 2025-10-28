# Flujo 01 - Fundamentos e infraestructura

## Objetivo

Garantizar que el equipo dispone de herramientas, configuraciones y accesos necesarios para ejecutar agentes en paralelo con modelos locales y remotos.

## Historias de usuario

- Como ingeniero quiero un entorno reproducible para instalar dependencias del curso y ejecutar agentes localmente.
- Como project manager quiero visibilidad del estado de instalacion y configuracion para anticipar bloqueos.

## Tareas

| ID | Tarea | Responsable sugerido | Estado | Dependencias |
| --- | --- | --- | --- | --- |
| FND-01 | Documentar hardware base disponible y gaps frente a requisitos | Project manager | Completado | Ninguna |
| FND-02 | Instalar Python 3.12, Git >= 2.25, VS Code y extensiones requeridas | Ingenieria | En curso | FND-01 |
| FND-03 | Crear entorno virtual `.venv` y validar `pip install -r requirements.txt` del curso | Ingenieria | Completado | FND-02 |
| FND-04 | Configurar WSL2 o subsistema equivalente para comandos Unix opcionales | Ingenieria | Completado | FND-02 |
| FND-05 | Establecer repositorio local con plantillas `.env` y scripts `setup.ps1`/`Makefile` | Ingenieria | Completado | FND-03 |
| FND-06 | Definir gestion de secretos (Vault, GitHub Secrets, archivos locales cifrados) | Seguridad | Completado | FND-05 |
| FND-07 | Verificar instalacion de Ollama y descarga de modelos prioritarios | Ingenieria | Completado | FND-02 |
| FND-08 | Crear checklist de verificacion de entorno para nuevos miembros | Project manager | Completado | FND-03 |

## Entregables

- Registro de capacidades de hardware y software.
- Script o guia de aprovisionamiento automatizado.
- Checklist de incorporacion documentado en el repositorio.

## Hardware Base y Gaps

### Especificaciones del Sistema

- **Nombre del PC**: KALISTA
- **Fabricante/Modelo de Motherboard**: Gigabyte Technology Co., Ltd. / B650 EAGLE AX
- **CPU**: AMD Ryzen 5 7600X (6 núcleos físicos, arquitectura Zen 4)
- **RAM**: Aproximadamente 32 GB (suficiente para modelos de IA locales y multitarea)
- **GPU**:
  - AMD Radeon(TM) Graphics (integrada): ~0.5 GB VRAM
  - NVIDIA GeForce GTX 1080: ~4 GB VRAM (soporte CUDA para aceleración en Ollama)

### Evaluación de Requisitos

- **Cobertura**: El hardware cumple con los requisitos básicos para desarrollo de agentes con modelos de IA locales (RAM >= 16 GB, CPU multicore, GPU con CUDA).
- **Gaps Identificados**:
  - VRAM limitada en GPU principal (4 GB) – potencial limitación para modelos muy grandes; recomendado escalar a 8 GB+ en futuras actualizaciones.
  - GPU no es de última generación, pero funcional para proyectos iniciales.

Esta documentación se basa en revisión del 28 de octubre de 2025.
