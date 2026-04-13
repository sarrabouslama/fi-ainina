# Common Commands

Quick reference for all important commands. Copy and paste as needed.

## Setup & Installation

### Install dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
cd frontend && npm install
cd ..
```

---

## Development - Local Mode

### Start API (FastAPI)
```bash
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

### Start Frontend (separate terminal)
```bash
cd frontend
npm run dev
```

---

## Development - Docker Mode

### Start all services
```bash
docker-compose up -d
```

### Stop all services
```bash
docker-compose down
```

### View logs
```bash
docker-compose logs -f
```

### View specific service logs
```bash
docker-compose logs -f api
docker-compose logs -f llm
docker-compose logs -f cv
docker-compose logs -f voice
docker-compose logs -f alerts
```

### Rebuild images
```bash
docker-compose build
```

---

## Testing

### Run all tests
```bash
pytest tests/ -v
```

### Run specific test file
```bash
pytest tests/test_api.py -v
```

### Run specific test function
```bash
pytest tests/test_api.py::test_api_health -v
```

---

## Cleanup

### Remove cache files
```bash
# Python caches
find . -type f -name '*.pyc' -delete
find . -type d -name '__pycache__' -delete
find . -type d -name '.pytest_cache' -delete

# Coverage reports
rm -rf htmlcov/ .coverage coverage.xml
```

---

## Full Development Workflow

```bash
# 1. Clone and setup
git clone <repo>
cd fi-ainina
pip install --upgrade pip
pip install -r requirements.txt
cd frontend && npm install && cd ..

# 2. Copy and edit environment
cp .env.example .env
# Edit .env with your API keys

# 3. Start development
# Terminal 1:
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2:
cd frontend && npm run dev

# 4. In another terminal, run tests
pytest tests/ -v

# 5. Commit changes
git add .
git commit -m "Your changes"
```
