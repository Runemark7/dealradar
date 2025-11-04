.PHONY: image run stop restart status logs logs-db clean dev test cli help
IMAGE_NAME := blocket-scraper
CONTAINER_NAME := blocket-scraper-api
PORT := 5000


help:
	@echo "Available targets:"
	@echo "  image       - Build the Docker image"
	@echo "  run         - Run API + database using docker-compose"
	@echo "  stop        - Stop all containers (docker-compose)"
	@echo "  restart     - Restart all containers"
	@echo "  status      - Show running services status"
	@echo "  logs        - View API container logs"
	@echo "  logs-db     - View database logs"
	@echo "  clean       - Remove containers, volumes, and images"
	@echo "  dev         - Run Flask API locally (dev mode)"
	@echo "  test        - Run pytest test suite"
	@echo "  cli         - Run CLI tool in container (usage: make cli ARGS='1213726656')"

image:
	@echo "Building container image..."
	docker build -t $(IMAGE_NAME):latest -f Containerfile .

run:
	@echo "Starting API + database with docker-compose..."
	@echo "(This will build the image if it doesn't exist)"
	docker-compose up -d --build
	@echo ""
	@echo "Services started:"
	@echo "  - API running at http://localhost:5000"
	@echo "  - PostgreSQL running at localhost:5432"
	@echo ""
	@echo "Use 'make logs' to view logs"
	@echo "Use 'make stop' to stop services"

stop:
	@echo "Stopping all containers..."
	docker-compose down

logs:
	@echo "Showing logs (Ctrl+C to exit)..."
	docker-compose logs -f blocket-scraper

logs-db:
	@echo "Showing database logs (Ctrl+C to exit)..."
	docker-compose logs -f postgres

clean: stop
	@echo "Removing containers and images..."
	docker-compose down -v
	-docker rmi $(IMAGE_NAME):latest

dev:
	@echo "Starting Flask API in development mode..."
	.venv/bin/python web_server.py

test:
	@echo "Running pytest test suite..."
	./run_tests.sh --ignore=tests/test_main.py

cli:
	@if [ -z "$(ARGS)" ]; then \
		echo "Usage: make cli ARGS='<ad_id>' or make cli ARGS='--search 5021 --limit 10'"; \
	else \
		docker run --rm $(IMAGE_NAME) .venv/bin/python -m dealradar.cli $(ARGS); \
	fi

restart: stop run

status:
	@echo "Services status:"
	@docker-compose ps
