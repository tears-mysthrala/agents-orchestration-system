# Guía de Extensibilidad para Agentes

## Visión General

Esta guía proporciona instrucciones completas para extender el sistema de agentes con nuevas funcionalidades. El sistema está diseñado para ser modular y extensible, permitiendo agregar nuevos agentes especializados sin modificar el código existente.

## Arquitectura del Sistema

### Componentes Principales

```bash
agents/
├── [agent_name].py          # Implementación del agente
├── __pycache__/
└── ...

config/
└── agents.config.json       # Configuración centralizada

prompts/
└── [agent_name].prompt      # Template de prompt

tests/
└── test_[agent_name].py     # Pruebas unitarias

docs/agents/
└── [agent_name]-agent.md    # Documentación del agente
```

### Principios de Diseño

- **Modularidad**: Cada agente es independiente y autocontenido
- **Configuración Centralizada**: Toda configuración en `agents.config.json`
- **Prompts Externos**: Separación de lógica y prompts
- **Testing Obligatorio**: Cobertura completa con pruebas unitarias
- **Documentación**: Guías actualizadas para cada agente

## Proceso de Adición de un Nuevo Agente

### Paso 1: Planificación

#### Definir el Rol del Agente

1. **Identificar la necesidad**: ¿Qué problema resuelve este agente?
2. **Definir responsabilidades**: ¿Qué tareas específicas ejecutará?
3. **Establecer interfaces**: ¿Qué inputs recibe? ¿Qué outputs produce?
4. **Determinar dependencias**: ¿Requiere outputs de otros agentes?

#### Seleccionar Modelo y Framework

1. **Evaluar complejidad**: ¿Requiere razonamiento avanzado o tareas simples?
2. **Considerar recursos**: ¿Qué modelos están disponibles localmente?
3. **Revisar compatibilidad**: ¿Funciona con CrewAI y Ollama?

**Ejemplo de definición:**

```json
{
  "id": "code_formatter",
  "description": "Formatea y estiliza código según estándares",
  "defaultModel": "codellama",
  "tools": ["black", "isort"],
  "outputs": ["formatted_code.py"],
  "requires": ["executor"]
}
```

### Paso 2: Implementación

#### Crear la Clase del Agente

**Estructura base obligatoria:**

```python
from crewai import Agent, Task, Crew, LLM
from pathlib import Path
import json

class [AgentName]Agent:
    def __init__(self, config_path: str = "config/agents.config.json"):
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.agent_config = self._get_agent_config()
        self.prompt_template = self._load_prompt_template()
        self._llm: Optional[LLM] = None

    def _load_config(self) -> Dict[str, Any]:
        # Implementación estándar de carga de config

    def _get_agent_config(self) -> Dict[str, Any]:
        # Obtener configuración específica del agente

    def _load_prompt_template(self) -> str:
        # Cargar template desde prompts/[agent_name].prompt

    def _initialize_llm(self) -> LLM:
        # Inicializar modelo con configuración de Ollama

    def create_agent(self) -> Agent:
        # Crear instancia de CrewAI Agent

    # Métodos específicos del agente...
```

**Patrón de métodos principales:**

```python
def execute_task(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
    """Método principal de ejecución."""
    # Formatear input
    # Crear Task con prompt personalizado
    # Ejecutar con Crew
    # Parsear y retornar resultado

def save_output(self, result: Dict[str, Any], path: str):
    """Guardar resultados en artifacts/."""
```

#### Crear Template de Prompt

**Ubicación:** `prompts/[agent_name].prompt`

**Estructura recomendada:**

```markdown
# Prompt para Agente [Nombre]

Eres un agente especializado en [descripción del rol].

## Instrucciones:
1. [Paso 1 específico]
2. [Paso 2 específico]
3. [Paso N específico]

## Formato de Salida:
- **[Sección 1]**: Descripción
- **[Sección 2]**: Detalles
- **[Sección N]**: Resultados

[Contexto específico]:
{{INPUT_DATA}}
```

**Variables de reemplazo:**

- Usa `{{VARIABLE_NAME}}` para datos dinámicos
- El agente reemplazará estas variables antes de enviar al modelo

### Paso 3: Configuración

#### Actualizar agents.config.json

**Ubicación de la entrada del agente:**

```json
{
  "agents": [
    {
      "id": "[agent_name]",
      "description": "Descripción clara del propósito",
      "entryPoint": "agents/[agent_name].py",
      "defaultModel": "[model_name]",
      "tools": ["tool1", "tool2"],
      "outputs": ["output1.ext", "output2.ext"],
      "requires": ["dependencia1", "dependencia2"]
    }
  ]
}
```

**Campos requeridos:**

- `id`: Identificador único (snake_case)
- `description`: Descripción en español
- `entryPoint`: Ruta relativa al archivo Python
- `defaultModel`: Modelo de `models.ollama`
- `tools`: Lista de herramientas utilizadas
- `outputs`: Archivos generados
- `requires`: Agentes previos necesarios

#### Verificar Modelo en Configuración

Asegurarse de que el modelo esté definido en `models.ollama`:

```json
{
  "models": {
    "ollama": {
      "[model_name]": {
        "temperature": 0.7,
        "context": 4096
      }
    }
  }
}
```

### Paso 4: Testing

#### Crear Suite de Pruebas

**Ubicación:** `tests/test_[agent_name].py`

**Estructura mínima:**

```python
import unittest
from agents.[agent_name] import [AgentName]Agent

class Test[AgentName]Agent(unittest.TestCase):
    def setUp(self):
        # Configurar entorno de pruebas

    def test_load_config_success(self):
        # Verificar carga de configuración

    def test_create_agent(self):
        # Verificar creación del agente CrewAI

    def test_execute_task(self):
        # Probar funcionalidad principal

    # Tests adicionales según funcionalidades
```

**Cobertura requerida:**

- ✅ Carga de configuración
- ✅ Manejo de errores
- ✅ Funcionalidad principal
- ✅ Integración con CrewAI
- ✅ Parsing de resultados
- ✅ Guardado de outputs

**Ejecutar pruebas:**

```bash
python -m unittest tests.test_[agent_name] -v
```

### Paso 5: Documentación

#### Crear Documentación del Agente

**Ubicación:** `docs/agents/[agent_name]-agent.md`

**Estructura recomendada:**

```markdown
# Agente [Nombre]

## Descripción

[Descripción detallada del propósito y funcionalidades]

## Arquitectura

### Framework
- **CrewAI**: Orquestación
- **Ollama**: Inferencia local
- **[Otros]**: Herramientas específicas

### Modelo Asignado
- **Modelo**: [Nombre del modelo]
- **Temperatura**: [Valor]
- **Contexto**: [Tokens]

## Funcionalidades

### [Función Principal 1]
- Descripción
- Inputs/Outputs
- Casos de uso

### [Función Principal 2]
- Descripción
- Inputs/Outputs
- Casos de uso

## Estructura de Código

```bash

agents/
├── [agent_name].py
└── ...

tests/
├── test_[agent_name].py
└── ...

docs/agents/
└── [agent_name]-agent.md

```

## Configuración

### Dependencias

- Lista de agentes requeridos
- Modelos necesarios
- Herramientas externas

### Parámetros

- Configuración en `agents.config.json`
- Variables de entorno
- Archivos de prompt

## Ejemplos de Uso

### Caso Básico

```python
from agents.[agent_name] import [AgentName]Agent

agent = [AgentName]Agent()
result = agent.execute_task(input_data)
```

### Integración con Pipeline

```python
# Después de agente anterior
previous_result = previous_agent.get_output()
result = agent.process_previous_output(previous_result)
```

## Métricas y Monitoreo

### KPIs

### Logs

- Ubicación: `logs/[agent_name].log`
- Formato: JSON estructurado
- Rotación: Diaria

## Troubleshooting

### Problemas Comunes

1. **Error de configuración**: Verificar `agents.config.json`
2. **Modelo no disponible**: Ejecutar `ollama pull [model_name]`
3. **Dependencias faltantes**: Instalar desde `requirements.txt`

### Debug Mode

```python
agent = [AgentName]Agent()
agent.set_debug(True)  # Habilitar logs detallados
```

## Extensibilidad Futura

### Hooks Disponibles

- `pre_execute`: Antes de la ejecución
- `post_execute`: Después de la ejecución
- `on_error`: Manejo de errores

### Extensiones Sugeridas

#### Actualizar README.md

Agregar entrada en la sección de agentes:

```markdown
### Agente [Nombre]
- **Propósito**: [Breve descripción]
- **Modelo**: [Modelo utilizado]
- **Estado**: ✅ Implementado
```

## Mejores Prácticas

### Desarrollo

1. **Principio de Responsabilidad Única**: Un agente = Una responsabilidad principal
2. **Configuración Externa**: Nunca hardcodear valores
3. **Manejo de Errores**: Graceful degradation, logging completo
4. **Testing First**: Escribir tests antes de la implementación
5. **Documentación Continua**: Actualizar docs con cada cambio

### Rendimiento

1. **Lazy Loading**: Inicializar modelos solo cuando se necesiten
2. **Caching**: Cachear resultados intermedios cuando sea posible
3. **Async Operations**: Usar async para operaciones I/O
4. **Resource Limits**: Configurar límites de memoria y CPU

### Seguridad

1. **Input Validation**: Validar todos los inputs
2. **Output Sanitization**: Sanitizar outputs antes de guardar
3. **Secrets Management**: Nunca loggear credenciales
4. **Access Control**: Verificar permisos según el contexto

## Ejemplos de Integración

### Agente con Dependencias

```python
# Agente A (planner) -> Agente B (executor)

# En planner.py
def generate_plan(self, requirements):
    plan = self.create_plan(requirements)
    return {
        "plan": plan,
        "next_agent": "executor",
        "artifacts": ["plan.md"]
    }

# En executor.py
def execute_plan(self, plan_data):
    plan = plan_data["plan"]
    # Ejecutar basado en el plan
    return self.run_execution(plan)
```

### Pipeline Completo

```python
from agents.planner import PlannerAgent
from agents.executor import ExecutorAgent
from agents.reviewer import ReviewerAgent

# Pipeline: Plan -> Execute -> Review
def run_pipeline(requirements):
    planner = PlannerAgent()
    plan = planner.plan_tasks(requirements)

    executor = ExecutorAgent()
    execution = executor.execute_task(plan)

    reviewer = ReviewerAgent()
    review = reviewer.review_code(execution)

    return {
        "plan": plan,
        "execution": execution,
        "review": review
    }
```

## Checklist de Validación

Antes de considerar el agente "completo":

- [ ] ✅ Implementación funcional
- [ ] ✅ Tests unitarios (cobertura > 80%)
- [ ] ✅ Documentación completa
- [ ] ✅ Configuración actualizada
- [ ] ✅ Integración con pipeline existente
- [ ] ✅ Validación de rendimiento
- [ ] ✅ Revisión de seguridad
- [ ] ✅ Aprobación de arquitectura

## Soporte y Mantenimiento

### Versionado

- Seguir [SemVer](https://semver.org/) para cambios
- Documentar breaking changes
- Mantener backward compatibility

### Monitoreo

- Logs estructurados en `logs/`
- Métricas en `artifacts/metrics/`
- Alertas para fallos críticos

### Actualizaciones

- Revisar dependencias mensualmente
- Actualizar modelos cuando estén disponibles
- Monitorear performance regressions

---

*Esta guía se actualiza con cada nuevo agente. Para contribuciones, seguir el proceso estándar de PR.*
