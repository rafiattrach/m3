# Makefile for M3 Docker Image Build and Push
DOCKER ?= docker
IMAGE_NAME := m3-mimic-demo
IMAGE_TAG ?= 0.4.0

# Prompt for registry only if not set
ifndef DOCKER_REGISTRY
DOCKER_REGISTRY := $(shell bash -c 'read -p "Enter Docker registry/username: " registry; echo $${registry}')
endif

DOCKER_IMAGE := $(DOCKER_REGISTRY)/$(IMAGE_NAME):$(IMAGE_TAG)

DB_FILE := m3_data/databases/mimic_iv_demo.db

.PHONY: help
help: ## Show help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-20s %s\n", $$1, $$2}'

.PHONY: all
all: download-db build push ## Complete workflow: download DB, build and push

.PHONY: login
login: ## Login to Docker Hub
	@$(DOCKER) login docker.io

.PHONY: download-db
download-db: ## Download MIMIC-IV demo database
	@uv sync
	@uv run m3 init mimic-iv-demo

.PHONY: build
build: ## Build Docker image (lite version)
	@test -f $(DB_FILE) || { echo "Run 'make download-db' first"; exit 1; }
	@$(DOCKER) build --target lite -t $(DOCKER_IMAGE) -t $(DOCKER_REGISTRY)/$(IMAGE_NAME):lite .

.PHONY: build-bigquery
build-bigquery: ## Build BigQuery version
	@test -f $(DB_FILE) || { echo "Run 'make download-db' first"; exit 1; }
	@$(DOCKER) build --target bigquery -t $(DOCKER_REGISTRY)/$(IMAGE_NAME):bigquery .

.PHONY: push
push: ## Push Docker image to registry (run 'make login' first)
	@$(DOCKER) push $(DOCKER_IMAGE)
	@$(DOCKER) push $(DOCKER_REGISTRY)/$(IMAGE_NAME):lite

.PHONY: push-bigquery
push-bigquery: ## Push BigQuery image (run 'make login' first)
	@$(DOCKER) push $(DOCKER_REGISTRY)/$(IMAGE_NAME):bigquery

.PHONY: test-image
test-image: ## Test the built Docker image
	@$(DOCKER) run --rm $(DOCKER_IMAGE) python -c "import m3; print(f'M3 version: {m3.__version__}')"

.PHONY: clean
clean: ## Remove database and raw files
	@rm -rf m3_data

.DEFAULT_GOAL := help
