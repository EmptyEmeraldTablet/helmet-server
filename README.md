# Helmet Server

FastAPI backend for helmet detection.

## Quick start

1. Activate the shared virtual environment:

```bash
source ../.venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Run the server:

```bash
uvicorn app.main:app --reload --port 8000
```

Health check: `GET /health`
