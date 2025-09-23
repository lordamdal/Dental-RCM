# Amdal Backend (CSV-first, FastAPI)

FastAPI backend that persists **cases**, **documents**, and **messages** in CSV files.
Includes a **per-case ChatGPT** endpoint that appends conversation to `messages.csv`.

Matches the frontend contract you have.

## Endpoints

- `GET /health`
- `GET /cases`
- `POST /cases`
- `GET /cases/{case_id}`
- `GET /cases/{case_id}/documents`
- `POST /cases/{case_id}/documents` (multipart)
- `GET /cases/{case_id}/messages`
- `POST /cases/{case_id}/chat` → calls OpenAI Chat Completions and appends assistant reply

> The UI/flow you shared expects a dashboard that updates as the user proceeds and a per-case chat with resume-later. This backend is designed for that.


## Quickstart

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# edit .env to put your ChatGPT API key

uvicorn app.main:app --reload
```

By default, files are saved under `data/` in the project root.

## Environment

- `OPENAI_API_KEY`: required
- Optional (Azure OpenAI): `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_DEPLOYMENT`

## CORS

CORS is wide-open for local dev. You can restrict `ALLOWED_ORIGINS` in `settings.py`.

## Notes

- CSV storage is append-only with simple upserts for `cases`.
- Uploads land in `data/uploads/{case_id}/` with a row added to `documents.csv`.
- Chat history is scoped by `case_id` and trimmed to the last N messages before calling the API.

