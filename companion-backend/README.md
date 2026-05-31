# Companion Backend (API Gateway)

FastAPI backend service for an elderly-care multimodal AI companion platform.

## Features
- JWT auth with access (15m) + refresh (7d in httpOnly cookie)
- Redis-backed token blacklist and login lockout (5 failed attempts / 15 min)
- User CRUD with role checks (`admin`, `caregiver`, `elderly`)
- GDPR endpoints:
  - Consent update: `POST /users/{id}/consent`
  - Right to erasure: `DELETE /users/{id}/data`
- WebSocket bridge from alerts service to backend
- Dashboard WebSocket endpoint for React clients: `ws://backend/ws/events?token=<access_token>`
- Aggregated dashboard endpoints
- Health checks + periodic upstream polling
- AES-style application-level encryption for sensitive JSON payloads

## Project Layout
- `app/` FastAPI application
- `alembic/` migrations
- `tests/` pytest suite
- `docker-compose.yml` backend + postgres + redis

## Quick Start
1. Copy env:
```bash
cp .env.example .env
```
2. Install deps:
```bash
pip install -r requirements.txt
```
3. Run app:
```bash
uvicorn app.main:app --reload
```

## Run with Docker
```bash
docker compose up --build
```

## Migrations
```bash
alembic upgrade head
```

## Tests
```bash
pytest -q
```

## GDPR Consent Clarification
`consent_given` means the elderly person has explicitly agreed to processing of personal data (video, audio, conversations) for monitoring and assistance.
