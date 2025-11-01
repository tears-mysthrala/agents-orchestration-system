#!/usr/bin/env python3
"""
Script para ejecutar la interfaz web de agentes.

Cross-platform compatible script for Windows 11 and Arch Linux.
Handles event loop differences and uvloop availability.
"""

import sys
import platform
from pathlib import Path

# Añadir el directorio raíz al path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))


def setup_event_loop():
    """Configure the best available event loop for the platform.
    
    - On Linux: Try to use uvloop if available for better performance
    - On Windows: Use standard asyncio (uvloop not available)
    """
    system = platform.system()
    
    if system == "Linux":
        try:
            import uvloop
            import asyncio
            asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
            print("✓ Using uvloop for better async performance")
        except ImportError:
            print("ℹ uvloop not available, using standard asyncio (install with: pip install uvloop)")
    elif system == "Windows":
        # Windows uses ProactorEventLoop by default in Python 3.8+
        # which is appropriate for Windows
        print("ℹ Using Windows ProactorEventLoop")
    else:
        print(f"ℹ Running on {system} with standard asyncio")


if __name__ == "__main__":
    import uvicorn
    
    # Setup optimal event loop for the platform
    setup_event_loop()
    
    print("\n" + "="*60)
    print("🚀 Starting Agent Orchestration Web Interface")
    print("="*60)
    print(f"Platform: {platform.system()} {platform.release()}")
    print(f"Python: {sys.version.split()[0]}")
    print(f"Server: http://127.0.0.1:8000")
    print(f"Dashboard: http://127.0.0.1:8000/static/dashboard.html")
    print("="*60 + "\n")
    
    # Run server
    uvicorn.run(
        "web.app:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info"
    )
