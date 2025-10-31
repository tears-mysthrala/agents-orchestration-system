#!/usr/bin/env python3
"""
Script para ejecutar la interfaz web de agentes.
"""

import uvicorn
import sys
from pathlib import Path

# Añadir el directorio raíz al path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

if __name__ == "__main__":
    uvicorn.run(
        "web.app:app", host="127.0.0.1", port=8000, reload=True, log_level="info"
    )
