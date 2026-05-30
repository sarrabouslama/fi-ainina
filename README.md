# FiAinina AI — Microservices Platform

AI-powered elderly care assistant with fall detection, voice companion, emotion monitoring, and family alerts.

## Team & Services

| Person | Service | Port | Tech |
|--------|---------|------|------|
| P1 | `llm_service` — LLM & Conversation | 8001 | OpenAI / Ollama |
| P2 | `voice_service` — Voice & Memory | 8002 | Whisper, TTS, PostgreSQL |
| P3 | `fall_detection_service` — Fall Detection | 8003 | MediaPipe, OpenCV |
| P4 | `emotion_service` — Inactivity & Emotion | 8004 | DeepFace, OpenCV |
| P5 | `alert_service` — Alerts & DevOps | 8005 | SMTP, Twilio, Docker |

## Quick Start

```bash
# 1. Clone the repo
git clone https://github.com/sarrabouslama/fi-ainina.git
cd fi-ainina

# 2. Setup environment files
make setup

# 3. Edit .env with your values (DB password, API keys, etc.)
nano .env

# 4. Start everything
make up

# 5. Check services are running
make ps
```

## Per-developer workflow

Each person only needs to start their service + infrastructure:

```bash
# P3 workflow
make up-infra          # start postgres + redis
make up-p3             # start fall_detection_service
make logs-p3           # follow logs
make test-p3           # run unit tests
```

## Service URLs (local)

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| API Gateway | http://localhost:80 |
| P1 LLM | http://localhost:8001/docs |
| P2 Voice | http://localhost:8002/docs |
| P3 Fall | http://localhost:8003/docs |
| P4 Emotion | http://localhost:8004/docs |
| P5 Alerts | http://localhost:8005/docs |
| PostgreSQL | localhost:5432 |
| Redis | localhost:6379 |

## Redis Event Contract

Services communicate via Redis Pub/Sub. **Do not change these channel names without coordinating with the team.**

| Channel | Producer | Consumer | Payload |
|---------|----------|----------|---------|
| `fall_events` | P3 | P5 | `FallEventPayload` (see P3 schemas.py) |
| `emotion_events` | P4 | P5 | emotion + person_id |
| `inactivity_events` | P4 | P5 | duration + person_id |
| `alerts` | P5 | Frontend WS | alert notification |

## Emotion Service Test Commands

Run the live camera preview from the project virtualenv:

```powershell
cd services/emotion_service
& 'C:\Users\UNICEF\Desktop\afc-doc\fi-ainina\.venv\Scripts\python.exe' camera_preview.py
```

Test a still image:

```powershell
& 'C:\Users\UNICEF\Desktop\afc-doc\fi-ainina\.venv\Scripts\python.exe' scripts/test_media.py --image path\to\face.jpg
```

Test a video file:

```powershell
& 'C:\Users\UNICEF\Desktop\afc-doc\fi-ainina\.venv\Scripts\python.exe' scripts/test_media.py --video path\to\video.mp4
```

Watch Redis alerts while the service runs:

```powershell
& 'C:\Users\UNICEF\Desktop\afc-doc\fi-ainina\.venv\Scripts\python.exe' scripts/redis_alert_listener.py
```

Check Redis pub/sub round-trip directly:

```powershell
& 'C:\Users\UNICEF\Desktop\afc-doc\fi-ainina\.venv\Scripts\python.exe' scripts/check_redis_pubsub.py
```

## Project Structure

```
fi-ainina/
├── docker-compose.yml       # Orchestration 
├── .env.example             # Root env template
├── Makefile                 # Dev shortcuts
└── infra/
    ├── nginx/             # API Gateway
    ├── postgres/init.sql  # DB schema
    ├── redis/redis.conf
├── monitoring/              # Prometheus + Grafana
├── frontend/                # React dashboard (shared)
└── services/
    ├── llm_service/         
    ├── voice_service/       
    ├── fall_detection_service/  
    ├── emotion_service/     
    └── alert_service/       
```


**Branch naming convention:** `feature/description`

## Environment Variables

- Root `.env` — shared infra config (DB, Redis URLs, JWT secret)
- `services/*/. env` — service-specific config (API keys, thresholds)
- `frontend/.env` — frontend URLs
