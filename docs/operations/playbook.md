# Playbook operativo

## Objetivo

Guiar la respuesta ante incidentes y el escalamiento operativo para agentes ejecutandose en paralelo.

## Preparacion previa

- Mantener `config/agents.config.json` sincronizado con la realidad de despliegue.
- Garantizar que los logs en `logs/` y artefactos en `artifacts/` se rotan segun la politica definida.
- Verificar semanalmente expiracion de tokens en gestores de secretos.

## Deteccion

1. Alertas automaticas desde monitoreo (latencia alta, error rate, uso de recursos).
2. Reportes manuales del equipo de desarrollo o usuarios finales.
3. Fallos en pipelines CI/CD antes de ejecutar agentes.

## Contencion

- Pausar ejecucion automatica con `scripts/run-agents.ps1 -DryRun` para evitar nuevos trabajos.
- Identificar agentes afectados consultando `logs/<agent>.log`.
- Si el problema esta ligado a un modelo remoto, cambiar temporalmente a un modelo local documentado en la configuracion.

## Erradicacion

- Aplicar parches en el agente correspondiente y validar con pruebas dirigidas.
- Actualizar configuraciones o secretos comprometidos.
- Registrar cambios en `docs/tasks` y en el sistema de control de versiones.

## Recuperacion

- Reanudar ejecuciones usando `scripts/run-agents.ps1` y monitorizar durante al menos un ciclo completo.
- Confirmar con los interesados que el servicio vuelvio a los niveles objetivos.

## Post-mortem

- Documentar resumen del incidente, linea temporal y acciones en `docs/operations/postmortems/<fecha>-<resumen>.md`.
- Identificar mejoras a procesos, tooling o monitoreo.
- Actualizar este playbook cuando se definan nuevos pasos estandar.
