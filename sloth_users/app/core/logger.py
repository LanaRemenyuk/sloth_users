from typing import Any

from app.core.config import settings

def get_logging_config(
    log_level: str | None = "INFO",
) -> dict[str, Any]:
    log_default_handlers: list[str] = [
        "console",
    ]

    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "verbose": {
                "()": "uvicorn.logging.DefaultFormatter",
                "fmt": "%(levelprefix)s [%(asctime)s] - %(message)s",
                "use_colors": True,
            },
            "default": {
                "()": "uvicorn.logging.DefaultFormatter",
                "fmt": "%(levelprefix)s [%(asctime)s] - %(message)s",
                "use_colors": True,
            },
            "access": {
                "()": "uvicorn.logging.AccessFormatter",
                "fmt": "%(levelprefix)s [%(asctime)s] - %(request_line)s %(status_code)s",
                "use_colors": True,
            },
        },
        "handlers": {
            "console": {
                "level": log_level,
                "class": "logging.StreamHandler",
                "formatter": "verbose",
            },
            "default": {
                "formatter": "default",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
            },
            "access": {
                "formatter": "access",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
            },
        },
        "loggers": {
            "": {
                "handlers": log_default_handlers,
                "level": log_level,
                "propagate": False,
            },
            "uvicorn": {
                "handlers": [
                    "default",
                ],
                "level": log_level,
                "propagate": False,
            },
            "uvicorn.error": {
                "level": log_level,
            },
            "uvicorn.access": {
                "handlers": [
                    "access",
                ],
                "level": log_level,
                "propagate": False,
            },
            "sqlalchemy": {
                "handlers": log_default_handlers,
                "level": log_level if settings.is_debug else "ERROR",
                "propagate": False,
            },
        },
        "root": {
            "level": log_level,
            "formatter": "verbose",
            "handlers": log_default_handlers,
        },
    }
