.PHONY: image run stop logs clean dev test help
IMAGE_NAME := blocket-scraper
CONTAINER_NAME := blocket-scraper-api
PORT := 5000

help:
	@echo "Available targets:"
	@echo "  image       - Build the image (runs tests first)"
	@echo "  run         - Run the API container"
	@echo "  stop        - Stop the running container"
	@echo "  logs        - View container logs"
	@echo "  clean       - Remove container and image"
	@echo "  dev         - Run Flask API locally (dev mode)"
	@echo "  test        - Run pytest test suite"
	@echo "  cli         - Run CLI tool in container (usage: make cli ARGS='1213726656')"

image: test
	@echo "Building container image..."
	docker build -t $(IMAGE_NAME) -f Containerfile .

run:
	@echo "Starting API container on port $(PORT)..."
	docker run -d --name $(CONTAINER_NAME) -p $(PORT):5000 $(IMAGE_NAME)
	@echo "API running at http://localhost:$(PORT)"

stop:
	@echo "Stopping container..."
	-docker stop $(CONTAINER_NAME)
	-docker rm $(CONTAINER_NAME)

logs:
	docker logs -f $(CONTAINER_NAME)

clean: stop
	@echo "Removing image..."
	-docker rmi $(IMAGE_NAME)

dev:
	@echo "Starting Flask API in development mode..."
	.venv/bin/python app.py

test:
	@echo "Running pytest test suite..."
	./run_tests.sh

cli:
	@if [ -z "$(ARGS)" ]; then \
		echo "Usage: make cli ARGS='<ad_id>' or make cli ARGS='--search 5021 --limit 10'"; \
	else \
		docker run --rm $(IMAGE_NAME) .venv/bin/python main.py $(ARGS); \
	fi

restart: stop run

status:
	@echo "Container status:"
	@docker ps -a | grep $(CONTAINER_NAME) || echo "Container not running"
	@echo ""
	@echo "Image info:"
	@docker images | grep $(IMAGE_NAME) || echo "Image not found"
