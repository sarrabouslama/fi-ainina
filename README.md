# AI Companion — Multimodal Safety System for Elderly Assistance

A real-time AI system combining conversational LLM, computer vision, voice interaction, and smart alerting.

## Project structure

```
services/   business logic — one package per module (llm, cv, voice, alerts)
api/        FastAPI routers and middleware — no business logic here
shared/     shared config, logger, constants
frontend/   React + vite dashboard
tests/      mirrors services/ — unit + integration
docker/     one Dockerfile per service
.github/    CI/CD workflows
```
## Stack

| Layer | Technology |
|-------|-----------|
| LLM | Ollama + LangChain |
| Computer Vision | MediaPipe + DeepFace + OpenCV |
| Voice | Whisper (STT) + Coqui TTS |
| Backend | Python 3.11 + FastAPI |
| Frontend | React 18 + Vite + Tailwind CSS |
| Database | PostgreSQL 16 + SQLAlchemy + Alembic |
| DevOps | Docker Compose + GitHub Actions |

## Environment variables

See `.env.example` for all required variables.

## Methodology

CRISP-DM phases mapped to Agile Epics — see `docs/crisp-dm.md`.
