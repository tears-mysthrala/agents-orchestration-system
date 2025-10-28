# Agente Planificador

## Descripción

El Agente Planificador es el componente inicial de la cadena de agentes orquestados. Su función principal es analizar entradas del backlog del usuario y generar planes de trabajo detallados, ordenados y priorizados.

## Arquitectura

### Framework

- **CrewAI**: Framework principal para orquestación de agentes
- **Ollama**: Motor de inferencia local para modelos de lenguaje
- **LangChain**: Integración y procesamiento de prompts (mínima en esta implementación)

### Modelo Asignado

- **Modelo**: Llama 3.2 (3B parameters)
- **Proveedor**: Ollama local
- **Temperatura**: 0.4 (balance entre creatividad y consistencia)
- **Contexto**: 8192 tokens

## Funcionalidades

### Análisis de Backlog

- Procesamiento de entradas estructuradas del backlog
- Identificación de prioridades, dependencias y estimaciones
- Validación de completitud de información

### Generación de Planes

- Creación de planes ordenados por prioridad y dependencias
- Estimación de tiempos y recursos
- Identificación de riesgos y obstáculos
- Formato estructurado en Markdown

### Integración con Sistema

- Carga automática de configuración desde `agents.config.json`
- Uso de templates de prompt desde `prompts/planner.prompt`
- Salida compatible con agentes downstream (executor, reviewer)

## Estructura de Código

```bash
agents/
├── planner.py              # Implementación principal del agente
└── ...

tests/
├── test_planner.py         # Suite de pruebas unitarias
└── ...

config/
├── agents.config.json      # Configuración del agente
└── ...

prompts/
├── planner.prompt          # Template de instrucciones
└── ...
```

## API

### Clase PlannerAgent

```python
from agents.planner import PlannerAgent

# Inicialización
agent = PlannerAgent(config_path="config/agents.config.json")

# Generación de plan
backlog_entries = [
    {
        "title": "Implementar autenticación",
        "description": "Sistema de login con JWT",
        "priority": "Alta",
        "estimate": "2 días",
        "dependencies": []
    }
]

plan = agent.plan_tasks(backlog_entries)

# Guardado del plan
agent.save_plan(plan, "artifacts/plan.md")
```

### Formato de Entrada (Backlog)

```python
backlog_entry = {
    "title": str,           # Título de la tarea
    "description": str,     # Descripción detallada
    "priority": str,        # "Alta", "Media", "Baja"
    "estimate": str,        # Estimación temporal (ej: "2 días")
    "dependencies": list    # Lista de títulos de tareas dependientes
}
```

### Formato de Salida (Plan)

```python
plan = {
    "plan_markdown": str,   # Contenido completo del plan en Markdown
    "status": str,          # "generated"
    "timestamp": str        # Timestamp ISO
}
```

## Configuración

### agents.config.json

```json
{
    "agents": [
        {
            "id": "planner",
            "defaultModel": "llama2",
            "tools": ["task-registry", "documentation-index"],
            "outputs": ["plan.md"]
        }
    ],
    "models": {
        "ollama": {
            "llama2": {
                "temperature": 0.2,
                "context": 4096
            }
        }
    }
}
```

### planner.prompt

Template de instrucciones que define:

- Rol y responsabilidades del agente
- Formato de entrada esperado
- Estructura de salida requerida
- Instrucciones específicas de planificación

## Pruebas

### Cobertura de Pruebas

- ✅ Inicialización y carga de configuración
- ✅ Manejo de errores (archivos no encontrados, JSON inválido)
- ✅ Procesamiento de entradas del backlog
- ✅ Integración con Ollama/CrewAI
- ✅ Generación y formateo de planes
- ✅ Guardado de resultados

### Ejecución de Pruebas

```bash
# Ejecutar todas las pruebas del planificador
python -m unittest tests.test_planner -v

# Ejecutar prueba específica
python -m unittest tests.test_planner.TestPlannerAgent.test_plan_tasks -v
```

## Dependencias

### Requerimientos

- crewai>=0.80.0
- langchain-ollama>=1.0.0
- ollama (servicio local)

### Modelos Requeridos

```bash
ollama pull llama3.2
```

## Limitaciones y Consideraciones

### Rendimiento

- Tiempo de respuesta: 10-30 segundos por plan
- Uso de memoria: ~4GB para modelo Llama 2
- Contexto limitado: 4096 tokens

### Escalabilidad

- Procesamiento secuencial (no paralelo)
- Un plan por ejecución
- Sin persistencia de estado entre ejecuciones

### Validación

- Requiere backlog bien estructurado
- Dependiente de calidad del modelo
- Sin validación automática de factibilidad

## Próximos Pasos

1. **Optimización**: Implementar procesamiento por lotes
2. **Persistencia**: Agregar base de datos para historial de planes
3. **Validación**: Integrar reglas de negocio para validación automática
4. **Interfaz**: Desarrollar API REST para integración externa
5. **Monitoreo**: Agregar métricas de rendimiento y calidad

## Troubleshooting

### Error: "LLM Provider NOT provided"

- Verificar que Ollama esté ejecutándose
- Confirmar que el modelo esté descargado
- Revisar configuración de `base_url` en `agents.config.json`

### Error: "FileNotFoundError" en prompts

- Verificar que existe `prompts/planner.prompt`
- Confirmar permisos de lectura
- Revisar path relativo desde directorio de ejecución

### Planes de baja calidad

- Ajustar temperatura del modelo (recomendado: 0.1-0.3)
- Mejorar calidad del prompt template
- Proporcionar backlog más detallado y estructurado
