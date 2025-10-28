"""
Configuración de logging estructurado para el proyecto de agentes.

Este módulo proporciona:
- Logging estructurado en formato JSON
- Configuración centralizada de logs
- Rotación automática de archivos
- Niveles de logging por componente
"""

import logging
import logging.config
import json
from datetime import datetime
from pathlib import Path


class StructuredFormatter(logging.Formatter):
    """Formateador personalizado para logs estructurados en JSON."""

    def format(self, record: logging.LogRecord) -> str:
        # Crear el mensaje estructurado
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Agregar campos extra si existen
        extra_fields = getattr(record, "extra_fields", {})
        if extra_fields:
            log_entry.update(extra_fields)

        # Agregar información de excepción si existe
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry, ensure_ascii=False)


def setup_logging(
    log_dir: str = "logs",
    log_level: str = "INFO",
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
) -> None:
    """
    Configurar el sistema de logging para toda la aplicación.

    Args:
        log_dir: Directorio donde guardar los logs
        log_level: Nivel de logging general
        max_bytes: Tamaño máximo de archivo antes de rotar
        backup_count: Número de archivos de backup a mantener
    """
    # Crear directorio de logs si no existe
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)

    # Configuración del logging
    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "structured": {
                "()": StructuredFormatter,
            },
            "console": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": log_level,
                "formatter": "console",
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "DEBUG",
                "formatter": "structured",
                "filename": str(log_path / "agents.log"),
                "maxBytes": max_bytes,
                "backupCount": backup_count,
                "encoding": "utf-8",
            },
            "error_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "ERROR",
                "formatter": "structured",
                "filename": str(log_path / "agents_error.log"),
                "maxBytes": max_bytes,
                "backupCount": backup_count,
                "encoding": "utf-8",
            },
        },
        "loggers": {
            "agents": {
                "level": log_level,
                "handlers": ["console", "file", "error_file"],
                "propagate": False,
            },
            "orchestration": {
                "level": log_level,
                "handlers": ["console", "file", "error_file"],
                "propagate": False,
            },
            "": {  # Root logger
                "level": "WARNING",
                "handlers": ["console"],
            },
        },
    }

    # Aplicar configuración
    logging.config.dictConfig(config)

    # Log inicial
    logger = logging.getLogger("agents")
    logger.info(
        "Sistema de logging configurado",
        extra={
            "extra_fields": {
                "log_directory": str(log_path),
                "log_level": log_level,
                "max_bytes": max_bytes,
                "backup_count": backup_count,
            }
        },
    )


def get_logger(name: str) -> logging.Logger:
    """
    Obtener un logger configurado para un módulo específico.

    Args:
        name: Nombre del logger (generalmente __name__)

    Returns:
        Logger configurado
    """
    return logging.getLogger(f"agents.{name}")


def log_execution_start(logger: logging.Logger, execution_id: str, **kwargs) -> None:
    """Log para el inicio de una ejecución."""
    logger.info(
        f"Ejecución iniciada: {execution_id}",
        extra={
            "extra_fields": {
                "execution_id": execution_id,
                "event": "execution_start",
                **kwargs,
            }
        },
    )


def log_execution_end(
    logger: logging.Logger, execution_id: str, status: str, **kwargs
) -> None:
    """Log para el fin de una ejecución."""
    logger.info(
        f"Ejecución finalizada: {execution_id} - {status}",
        extra={
            "extra_fields": {
                "execution_id": execution_id,
                "event": "execution_end",
                "status": status,
                **kwargs,
            }
        },
    )


def log_agent_action(
    logger: logging.Logger, agent_name: str, action: str, **kwargs
) -> None:
    """Log para acciones de agentes."""
    logger.info(
        f"Agente {agent_name}: {action}",
        extra={"extra_fields": {"agent": agent_name, "action": action, **kwargs}},
    )


def log_error(logger: logging.Logger, error: Exception, **kwargs) -> None:
    """Log para errores con contexto adicional."""
    logger.error(
        f"Error: {str(error)}",
        exc_info=True,
        extra={"extra_fields": {"error_type": type(error).__name__, **kwargs}},
    )


# Configuración por defecto al importar
if __name__ != "__main__":
    # Solo configurar si no estamos ejecutando como script principal
    setup_logging()
