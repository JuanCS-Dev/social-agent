# Social Agent

## About
Autonomous multi-platform social agent with webhook ingestion (Reddit/Meta), OODA loop processing, policy guardrails, and Cloud Run deployment automation.

This repository is isolated from any other existing Cloud Run bot/service.

## Stack
- Python + FastAPI
- Vertex AI (Gemini via `google-genai`)
- SQLite (MVP queue + idempotency + DLQ)
- Cloud Run + Cloud Build + Secret Manager
- Cloud Monitoring + log-based metrics

## Deploy (quick path)
1. `cp ops/cloudrun/deploy.env.example ops/cloudrun/deploy.env`
2. `cp ops/cloudrun/secrets.env.example ops/cloudrun/secrets.env`
3. Fill project and credentials.
4. `./ops/cloudrun/bootstrap_gcp.sh ops/cloudrun/deploy.env`
5. `./ops/cloudrun/sync_secrets.sh ops/cloudrun/deploy.env ops/cloudrun/secrets.env`
6. `./ops/cloudrun/deploy.sh ops/cloudrun/deploy.env`
7. `./ops/observability/setup_observability.sh ops/cloudrun/deploy.env`

Detailed docs are in `docs/passo_a_passo_deploy_anti_burro.md` and `docs/roadmap_implantacao_social_agent_cloudrun.md`.
