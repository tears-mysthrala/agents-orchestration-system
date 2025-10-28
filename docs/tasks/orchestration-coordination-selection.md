# ORC-01: Selección de Mecanismo de Coordinación

## Decisión

Se ha seleccionado **APScheduler** como mecanismo principal de coordinación para el sistema de agentes, complementado con una capa de coordinación personalizada (`AgentCoordinator`).

## Justificación

### Análisis de Opciones

| Opción | Ventajas | Desventajas | Adecuación |
|--------|----------|-------------|------------|
| APScheduler | Scheduling flexible (cron, intervalos), ejecución en background, integración con async, ligero y confiable | No maneja workflows complejos nativamente | ⭐ Seleccionado |
| Celery + Redis | Distribuido y escalable, colas robustas, monitoreo avanzado | Sobredimensionado para sistema local, requiere infraestructura adicional | ❌ Demasiado complejo |
| Airflow/Prefect | Workflows complejos, UI de monitoreo, DAGs para dependencias | Sobredimensionado, curva de aprendizaje alta, requiere base de datos | ❌ Overkill |
| Event Bus (Redis/pub) | Desacoplamiento, comunicación asíncrona | No maneja scheduling, requiere coordinación adicional | ❌ Incompleto |

### Arquitectura Seleccionada

```markdown
┌─────────────────┐    ┌──────────────────┐
│   AgentCoordinator  │───│   APScheduler     │
│                     │    │                  │
│ - Workflow logic    │    │ - Cron jobs      │
│ - Dependencies      │    │ - Intervals      │
│ - Error handling    │    │ - Background exec│
│ - State management  │    │                  │
└─────────────────┘    └──────────────────┘
         │
         ▼
┌─────────────────┐
│   Agent Pool    │
│                 │
│ - PlannerAgent  │
│ - ExecutorAgent │
│ - ReviewerAgent │
└─────────────────┘
```

## Implementación

### Componentes Principales

1. **AgentCoordinator**: Clase principal que gestiona la ejecución de workflows
2. **WorkflowStep**: Define pasos individuales con dependencias y configuración
3. **WorkflowExecution**: Rastrea el estado y resultados de ejecuciones completas
4. **BackgroundScheduler**: Maneja la programación automática de ejecuciones

### Workflow Estándar

```markdown
PlannerAgent → ExecutorAgent → ReviewerAgent
     ↓             ↓             ↓
   Planificar   Ejecutar      Revisar
   tareas       tareas        resultados
```

### Características Implementadas

- ✅ Scheduling flexible: Expresiones cron e intervalos
- ✅ Manejo de dependencias: Pasos se ejecutan en orden correcto
- ✅ Reintentos: Lógica de retry con backoff exponencial
- ✅ Timeouts: Límite de tiempo por paso
- ✅ Estado y logging: Seguimiento completo de ejecuciones
- ✅ Historial: Registro de ejecuciones pasadas

## Uso

### Ejecución Manual

```python
from orchestration.coordinator import run_standard_workflow

result = run_standard_workflow()
print(f"Workflow completado: {result.state}")
```

### Scheduling Automático

```python
from orchestration.coordinator import schedule_daily_workflow

job_id = schedule_daily_workflow(hour=9, minute=0)  # 9:00 AM diario
```

## Beneficios

1. **Simplicidad**: Solución ligera apropiada para el alcance actual
2. **Flexibilidad**: Fácil de extender para workflows más complejos
3. **Confiabilidad**: APScheduler es una librería madura y probada
4. **Escalabilidad**: Arquitectura preparada para crecimiento futuro
5. **Mantenibilidad**: Código claro y bien documentado

## Consideraciones Futuras

- Si el sistema crece significativamente, considerar migrar a Celery
- Para workflows muy complejos, evaluar Prefect o Airflow
- Monitoreo adicional podría requerir integración con herramientas como Prometheus

## Testing

Se incluyen pruebas unitarias para validar:

- Ejecución correcta de workflows
- Manejo de dependencias
- Lógica de reintentos
- Scheduling automático
- Manejo de errores

---

**Estado**: ✅ **Completado**
**Fecha**: 28/10/2025 - 21:45
**Responsable**: Arquitectura
