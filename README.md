# EM-Aide (MVP) — Local Data + Remote LLM with plans for local LLM

EM-Aide is a local, privacy-first Engineering Manager Copilot:
- Ingests Jira Cloud + GitHub (Cloud or Enterprise via base URL) **into a local Postgres DB**
- Computes delivery + dev-flow signals locally
- Builds a **strictly sanitized** context packet (no code, no diffs, no ticket text)
- Uses an **OpenAI-compatible** LLM endpoint to generate:
  - Weekly top-3 actions
  - Top-5 risks
- Stores plans + runs for audit/debugging

## Quick start

1) Copy env file and fill tokens:

```bash
cp .env.example .env
```

2) Start:

```bash
docker compose up -d --build
```

3) Open React dashboard:

- http://localhost:8080/app

## GitHub Cloud vs Enterprise
Set `GITHUB_API_BASE_URL`:
- GitHub Cloud default: `https://api.github.com`
- GitHub Enterprise Server: `https://<your-ghe-domain>/api/v3`

## LLM Support
This MVP uses an OpenAI-compatible endpoint.
Set:
- `LLM_BASE_URL`
- `LLM_API_KEY`
- `LLM_MODEL`

Only **sanitized metrics & IDs** are sent to the LLM.

## Whats in cards
There is a stub `OllamaClient` you can enable later via:
- `LLM_MODE=local`
- `OLLAMA_BASE_URL=http://host.docker.internal:11434`
- `OLLAMA_MODEL=...`

## Jobs
Worker runs:
- GitHub sync (default hourly)
- Jira sync (default hourly; optional if unset)
- Metrics snapshot (daily)
- Weekly plan generation (manual endpoint now; can be scheduled)

## Important privacy note
EM-Aide does **not** send:
- issue titles/descriptions/comments
- PR diffs or code
- secrets

It sends:
- counts, durations, statuses, sizes, anonymized IDs, and aggregated signals.
