# Makefile — Alert Service Development Commands

.PHONY: help install test test-unit test-integration test-cov dev logs clean test-email test-sms test-whatsapp

help:
	@echo "Alert Service — Development Commands"
	@echo "===================================="
	@echo ""
	@echo "make install        — Install dependencies"
	@echo "make dev            — Start service in development mode"
	@echo "make logs           — View service logs (follow)"
	@echo "make test           — Run all tests"
	@echo "make test-unit      — Run unit tests only"
	@echo "make test-cov       — Run tests with coverage report"
	@echo "make test-alert     — Send test alert via API"
	@echo "make test-email     — Send test email via SMTP"
	@echo "make test-sms       — Send test SMS via Twilio"
	@echo "make test-whatsapp  — Send test WhatsApp via Twilio"
	@echo "make redis-cli      — Connect to Redis CLI"
	@echo "make psql           — Connect to PostgreSQL"
	@echo "make clean          — Clean up containers and volumes"
	@echo "make format         — Format code with black"
	@echo "make lint           — Lint code with pylint"
	@echo ""

install:
	pip install -r requirements.txt

dev:
	docker-compose up alert_service

logs:
	docker logs fi_ainina_alert -f

test:
	pytest tests/ -v

test-unit:
	pytest tests/ -v -m "not integration"

test-cov:
	pytest tests/ --cov=app --cov-report=html --cov-report=term
	@echo "Coverage report generated in htmlcov/index.html"

test-alert:
	@echo "Sending test alert..."
	curl -X POST http://localhost:8005/alerts/test \
		-H "Content-Type: application/json" \
		-d '{ \
			"event_type": "fall_detected", \
			"user_id": "elder_test_001", \
			"severity": "high", \
			"metadata": {"confidence": 0.95} \
		}' | jq

test-email:
	@echo "Running SMTP email test script..."
	python app/scripts/test_email.py

test-whatsapp:
	@echo "Running Twilio WhatsApp test script..."
	python app/scripts/test_whatsapp.py

test-health:
	@echo "Checking Alert Service health..."
	curl http://localhost:8005/health | jq

test-history:
	@echo "Fetching alert history..."
	curl "http://localhost:8005/alerts?limit=5" | jq

redis-cli:
	docker exec -it fi_ainina_redis redis-cli

psql:
	docker exec -it fi_ainina_postgres psql -U postgres -d fi_ainina

redis-pubsub-test:
	@echo "Publishing test alert to Redis..."
	docker exec -it fi_ainina_redis redis-cli PUBLISH fall_events \
		'{"event_type":"fall_detected","user_id":"elder_001","timestamp":"2025-05-01T12:00:00Z","severity":"high","confidence":0.95,"metadata":{}}'

clean:
	docker-compose down -v

format:
	black app/ tests/

lint:
	pylint app/

.PHONY: help install dev logs test test-unit test-cov test-alert test-email test-sms test-whatsapp test-health redis-cli psql clean format lint
