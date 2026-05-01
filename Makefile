# ============================================================
# FiAinina AI — Makefile for Windows
# Usage: make <target>
# ============================================================

.PHONY: help setup up down restart logs ps build clean

help:
	@echo ""
	@echo "FiAinina AI — Available commands:"
	@echo "  make setup      Copy .env.example → .env (first time)"
	@echo "  make up         Start all services"
	@echo "  make down       Stop all services"
	@echo "  make restart    Restart all services"
	@echo "  make build      Rebuild all Docker images"
	@echo "  make logs       Follow logs of all services"
	@echo "  make ps         Show running containers"
	@echo "  make clean      Remove volumes and containers"
	@echo ""
	@echo "Per-service:"
	@echo "  make up-p5      Start alert_service + deps"
	@echo "  make logs-p5    Follow logs of alert_service"
	@echo ""

setup:
	@echo "Setting up environment..."
	@if not exist .env copy .env.example .env
	@if not exist services\llm_service\.env copy services\llm_service\.env.example services\llm_service\.env
	@if not exist services\voice_service\.env copy services\voice_service\.env.example services\voice_service\.env
	@if not exist services\fall_detection_service\.env copy services\fall_detection_service\.env.example services\fall_detection_service\.env
	@if not exist services\emotion_service\.env copy services\emotion_service\.env.example services\emotion_service\.env
	@if not exist services\alert_service\.env copy services\alert_service\.env.example services\alert_service\.env
	@if not exist frontend\.env copy frontend\.env.example frontend\.env
	@echo "✓ Setup complete! Edit .env files with your credentials."

up:
	docker compose up -d

down:
	docker compose down

restart:
	docker compose down && docker compose up -d

build:
	docker compose build

logs:
	docker compose logs -f

ps:
	docker compose ps

clean:
	docker compose down -v --remove-orphans

# ─── Per-service shortcuts ───────────────────────────────────

up-p1:
	docker compose up -d postgres redis llm_service

up-p2:
	docker compose up -d postgres redis voice_service

up-p3:
	docker compose up -d redis fall_detection_service

up-p4:
	docker compose up -d redis emotion_service

up-p5:
	docker compose up -d postgres redis alert_service

up-infra:
	docker compose up -d postgres redis

logs-p1:
	docker compose logs -f llm_service

logs-p2:
	docker compose logs -f voice_service

logs-p3:
	docker compose logs -f fall_detection_service

logs-p4:
	docker compose logs -f emotion_service

logs-p5:
	docker compose logs -f alert_service

test-p3:
	docker compose exec fall_detection_service python -m pytest tests/ -v

monitoring:
	docker compose --profile monitoring up -d prometheus grafana