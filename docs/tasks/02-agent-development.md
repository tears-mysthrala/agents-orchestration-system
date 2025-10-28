# Flujo 02 - Diseno y desarrollo de agentes

## Objetivo

Construir agentes especializados que automaticen tareas de desarrollo y colaboren entre si.

## Historias de usuario

- Como arquitecto quiero disenar roles y responsabilidades de cada agente para evitar solapamientos.
- Como ingeniero quiero plantillas de agente para reutilizar componentes y acelerar nuevas iteraciones.

## Tareas

| ID | Tarea | Responsable sugerido | Estado | Dependencias |
| --- | --- | --- | --- | --- |
| AGT-01 | Definir matriz RACI por agente (planificador, ejecutor, revisor, etc.) | Arquitectura | Completado | FND-05 |
| AGT-02 | Seleccionar frameworks base segun casos de uso | Arquitectura | Completado | AGT-01 |
| AGT-03 | Crear repositorio de configuraciones compartidas (`agents.config.json`, `.prompt`) | Ingenieria | Completado | AGT-02 |
| AGT-04 | Implementar agente planificador con pruebas unitarias | Ingenieria | Completado | AGT-03 |
| AGT-05 | Implementar agente ejecutor con integracion a repositorios de codigo | Ingenieria | Pendiente | AGT-04 |
| AGT-06 | Implementar agente revisor con capacidad de sugerir mejoras | Ingenieria | Pendiente | AGT-05 |
| AGT-07 | Documentar guias de extensibilidad para nuevos agentes | Arquitectura | Pendiente | AGT-06 |
| AGT-08 | Validar compatibilidad de agentes con modelos locales (Ollama) y remotos | Ingenieria | Pendiente | AGT-04 |

## Entregables

- Matriz de responsabilidades y contratos de interaccion.
- Codigo de agentes base con pruebas unitarias.
- Documentacion de extensibilidad y configuraciones compartidas.

## Matriz RACI y Especificaciones de Agentes

### Agentes Definidos

Basado en el flujo de trabajo orquestado, se definen 5 agentes especializados con modelos locales optimizados para el hardware disponible (Ryzen 5 7600X, 32 GB RAM, GTX 1080).

#### 1. Agente Planificador

- **Modelo Asignado**: DeepSeek Chat 7B (`deepseek-chat`)
- **Tareas**: Generar planes detallados a partir de directrices básicas, priorizar tareas, estimar recursos.
- **RACI**:
  - Responsible: Agente Planificador
  - Accountable: Usuario (líder del proyecto)
  - Consulted: Agente Revisor (para validación de viabilidad)
  - Informed: Todos los agentes

#### 2. Agente Ejecutor

- **Modelo Asignado**: DeepSeek Coder 6.7B (`deepseek-coder`)
- **Tareas**: Ejecutar código, integrar con repositorios, correr pruebas unitarias.
- **RACI**:
  - Responsible: Agente Ejecutor
  - Accountable: Usuario
  - Consulted: Agente Planificador (para ajustes en plan)
  - Informed: Agente Revisor

#### 3. Agente Revisor

- **Modelo Asignado**: Gemma 2 9B (`gemma2`)
- **Tareas**: Evaluar rendimiento, sugerir mejoras, analizar métricas de efectividad.
- **RACI**:
  - Responsible: Agente Revisor
  - Accountable: Usuario
  - Consulted: Agente Diagnóstico (para datos de problemas)
  - Informed: Todos los agentes

#### 4. Agente Diagnóstico

- **Modelo Asignado**: Phi-3.5 3.8B (`phi3.5`)
- **Tareas**: Monitorear logs, detectar errores, alertar sobre cuellos de botella.
- **RACI**:
  - Responsible: Agente Diagnóstico
  - Accountable: Usuario
  - Consulted: Agente Revisor (para análisis de incidentes)
  - Informed: Agente Comunicación

#### 5. Agente Comunicación

- **Modelo Asignado**: Llama 3.2 3B (`llama3.2`)
- **Tareas**: Solicitar feedback humano via Telegram/Discord, integrar respuestas en flujo.
- **RACI**:
  - Responsible: Agente Comunicación
  - Accountable: Usuario
  - Consulted: Todos los agentes (para contexto de mensajes)
  - Informed: Usuario (feedback directo)

### Frameworks Base Seleccionados

Basado en casos de uso para agentes orquestados (colaboración, integración con modelos locales/remotos, comunicación externa):

- **CrewAI**: Framework principal para equipos de agentes colaborativos con roles definidos (ej. planificador, ejecutor). Ya instalado; ideal para orquestación central.
- **LangChain**: Para integración con LLMs (Ollama, OpenAI) y herramientas externas. Complementa CrewAI con chains y prompts.
- **AutoGen**: Para comunicación multi-agente avanzada y chat entre agentes. Requerido para feedback externo (Telegram/Discord) y colaboración autónoma.

**Justificación**: AutoGen es esencial para el agente de comunicación y orquestación dinámica; compatible con CrewAI/LangChain. Versión pinned (0.2.35) para estabilidad.

Completado: 28/10/2025 - 21:07
