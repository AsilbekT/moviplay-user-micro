.PHONY: proto run test test-cov lint clean venv install help

APP_NAME := user-service
GRPC_PORT := 50051
PYTHON := python3
VENV := venv

## proto: Generate Python protobuf code from shared/proto/users.proto (canonical source)
proto:
	@$(VENV)/bin/python create_proto.py

## sync-proto: Copy canonical users.proto from shared to local proto dir (for reference)
sync-proto:
	@echo "Syncing users.proto from shared/proto..."
	@cp ../shared/proto/users.proto proto/users.proto
	@echo "Done."

## run: Run the gRPC server
run:
	@$(VENV)/bin/python server.py

## test: Run tests
test:
	@$(VENV)/bin/pytest tests/ -v

## test-cov: Run tests with coverage
test-cov:
	@$(VENV)/bin/pytest tests/ -v --cov=services --cov=utils --cov-report=html
	@echo "Coverage report: htmlcov/index.html"

## lint: Run linters
lint:
	@$(VENV)/bin/flake8 services/ utils/ tests/ --max-line-length=120
	@$(VENV)/bin/black --check services/ utils/ tests/

## fmt: Format code
fmt:
	@$(VENV)/bin/black services/ utils/ tests/
	@echo "Formatted."

## clean: Remove generated files and caches
clean:
	@rm -rf __pycache__ .pytest_cache htmlcov .coverage
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@echo "Cleaned."

## venv: Create virtual environment
venv:
	@$(PYTHON) -m venv $(VENV)
	@echo "Virtual environment created. Run 'make install' to install dependencies."

## install: Install dependencies
install:
	@$(VENV)/bin/pip install -r requirements.txt
	@echo "Dependencies installed."

## help: Show this help
help:
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@sed -n 's/^##//p' $(MAKEFILE_LIST) | column -t -s ':' | sed 's/^/ /'

.DEFAULT_GOAL := help
