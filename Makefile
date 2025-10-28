# Makefile para proyecto de agentes IA

.PHONY: setup install clean test run run-parallel coordinator help

# Configuración
VENV = .venv
PYTHON = $(VENV)/Scripts/python.exe
PIP = $(VENV)/Scripts/pip.exe
INVOKE = $(VENV)/Scripts/invoke.exe

# Comandos principales
setup: $(VENV)
	@echo "Entorno configurado. Activa con: source $(VENV)/Scripts/activate"

$(VENV):
	python -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

install:
	$(PIP) install -r requirements.txt

clean:
	rm -rf $(VENV)
	rm -rf __pycache__
	rm -rf *.pyc
	rm -rf .pytest_cache
	rm -rf logs

test:
	$(PYTHON) -m pytest

run:
	@echo "Ejecutando agentes..."
	$(PYTHON) -c "import crewai; print('Agentes listos')"

run-parallel:
	@echo "Ejecutando agentes en paralelo..."
	$(INVOKE) run-parallel

coordinator:
	@echo "Ejecutando coordinador..."
	$(INVOKE) coordinator-run

help:
	@echo "Comandos disponibles:"
	@echo "  setup        - Configurar entorno virtual"
	@echo "  install      - Instalar dependencias"
	@echo "  clean        - Limpiar entorno"
	@echo "  test         - Ejecutar tests"
	@echo "  run          - Ejecutar agentes (legacy)"
	@echo "  run-parallel - Ejecutar agentes en paralelo"
	@echo "  coordinator  - Ejecutar via coordinador"
	@echo "  help         - Mostrar esta ayuda"