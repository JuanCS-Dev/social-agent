# Byte Social Agent - System Documentation

Last updated: 2026-02-21

## 1. Purpose and Scope

Byte Social Agent is an autonomous social-media runtime that:

1. Ingests platform signals (webhooks and external triggers).
2. Classifies context and decides actions via an OODA loop.
3. Executes publish/reply actions through APIs or an operator queue.
4. Self-adjusts daily strategy based on recent performance signals.

This repository is an independent service and must not be confused with other agents deployed in the same GCP project.

## 2. Runtime Topology

Single Cloud Run service process with two concurrent responsibilities:

1. FastAPI ingestion/ops HTTP API.
2. Background `AutonomyLoop` task started on app startup.

Recommended runtime entrypoint:

```bash
uvicorn src.app.server:fastapi_app --host 0.0.0.0 --port 8000
```

## 3. Architecture Layers

1. Ingestion Layer: receives events and stores raw payloads (`events`).
2. Cognitive Layer: classify -> reason -> propose actions (`AutonomyLoop` + `UnderstandEngine` + `AutonomyStrategy`).
3. Execution Layer: budget/policy checks + connector calls (`ActionDispatcher` + connectors).
4. Ops Layer: queue stats, operator task lifecycle, observability scripts.

## 4. Source Map (What Lives Where)

| Area | Main files | Responsibility |
| --- | --- | --- |
| HTTP API | `src/ingestion/app.py`, `src/ingestion/routers/webhooks.py`, `src/ingestion/routers/ops.py` | Webhooks, health, ops endpoints |
| Runtime orchestration | `src/app/server.py`, `src/agent/loop.py` | Starts background loop and handles OODA ticks |
| LLM + reasoning | `src/agent/understand.py`, `src/agent/persona.py`, `src/agent/intelligence.py` | Classification, generation, daily strategy |
| Strategy | `src/agent/strategy.py`, `src/agent/profiles.py` | Reactive/proactive proposals and per-platform profile behavior |
| Action execution | `src/agent/act.py`, `src/connectors/*.py` | Dispatch, policy gating, API integrations |
| Safety/policy | `src/policy/engine.py` | Allow/block decisions and risk level |
| Budgeting/autoregulation | `src/planner/scheduler.py` | Daily budgets, cooldown, publish interval control |
| Persistence | `src/memory/storage.py` | SQLite queue, DLQ, logs, reflections, operator tasks |
| Deployment/Ops | `ops/cloudrun/*`, `ops/observability/*` | Bootstrap, secret sync, predeploy checks, deploy, metrics/dashboard |

## 5. OODA Lifecycle

### 5.1 Reactive Flow

1. Platform signal hits `/webhooks/*`.
2. Payload is persisted as `events`.
3. `AutonomyLoop.tick()` fetches oldest pending event.
4. `UnderstandEngine.classify()` returns intent/urgency/language.
5. `AutonomyStrategy.build_reactive_proposals()` builds reply proposal when required.
6. Dispatcher executes action via connector or queues operator task.
7. Result is saved in `action_logs`; failures can move event to `dlq`.

### 5.2 Proactive Flow

Runs when queue is empty and `AUTONOMY_ENABLE_PROACTIVE=1`:

1. Strategy extracts recent reflection context (topics + narrative + KPI targets).
2. Generates post per platform rotation and readiness checks.
3. Appends CTA in dominant mode.
4. Executes publish or enqueues operator fallback.

### 5.3 Daily Reflection Flow

Runs once per UTC day:

1. Reads last 24h `trend_signals`.
2. Builds market brief and growth KPI summary.
3. Generates 24h strategy (`summary`, topics, narrative, KPI targets).
4. Saves into `daily_reflections`.

## 6. Platform Execution Matrix

| Platform | Ingestion endpoint | Execution mode | API fallback |
| --- | --- | --- | --- |
| Reddit | `POST /webhooks/reddit` | API | If API fails and fallback enabled -> `operator_tasks` |
| X | `POST /webhooks/x` | `api` or `operator` via `X_EXECUTION_MODE` | `operator` mode is primary no-cost path |
| Facebook | `POST /webhooks/meta` | API | If API fails and fallback enabled -> `operator_tasks` |
| Instagram | `POST /webhooks/meta` | API | If API fails and fallback enabled -> `operator_tasks` |

Reference: `docs/webhook_contracts.md`, `docs/x_operacao_sem_api_paga.md`.

## 7. API Surface

### 7.1 Public/Ingress

1. `GET /health`
2. `POST /webhooks/reddit`
3. `POST /webhooks/x` (token check if configured)
4. `POST /webhooks/meta` (signature enforced in production)
5. `GET /webhooks/meta` (Meta verification challenge)

### 7.2 Ops

1. `GET /ops/status`
2. `GET /ops/operator/tasks?platform=x&status=pending&limit=50`
3. `POST /ops/operator/tasks/{task_id}/complete`

## 8. Persistence Model (SQLite)

| Table | Purpose |
| --- | --- |
| `events` | Pending raw webhook events |
| `dlq` | Failed events for replay/investigation |
| `action_logs` | Audit trail of action results |
| `trend_signals` | Structured context features + metadata |
| `daily_reflections` | Daily strategy payload |
| `operator_tasks` | Manual execution queue and status |
| `idempotency` | Keys to avoid duplicate side effects |

Default path in local runtime: `./var/data/social_agent.db`.

## 9. Configuration Model

Primary settings are loaded from environment variables (`src/core/config.py`).

Critical variables:

1. Runtime: `ENVIRONMENT`, `AUTONOMY_*`, `DATABASE_URL`.
2. LLM: `GCP_PROJECT`, `GCP_LOCATION`, grounding flags.
3. Editorial persona: `AGENT_GOAL`, `AGENT_IDEOLOGY`, `AGENT_MORAL_FRAMEWORK`, `AGENT_DOMINANT_MODE`, `AGENT_PRIMARY_CTA`.
4. Platform secrets: Reddit, Meta, X.
5. X mode selector: `X_EXECUTION_MODE=api|operator`.

Detailed references:

1. `docs/deploy_env_vars.md`
2. `docs/deploy_secrets_matrix.md`
3. `docs/conectar_contas_plataformas_anti_burro.md`

## 10. Deployment and Environment Control

Standard sequence:

```bash
cp ops/cloudrun/deploy.env.example ops/cloudrun/deploy.env
cp ops/cloudrun/secrets.env.example ops/cloudrun/secrets.env
./ops/cloudrun/bootstrap_gcp.sh ops/cloudrun/deploy.env
./ops/cloudrun/sync_secrets.sh ops/cloudrun/deploy.env ops/cloudrun/secrets.env
./ops/cloudrun/predeploy_check.sh ops/cloudrun/deploy.env
./ops/cloudrun/deploy.sh ops/cloudrun/deploy.env
./ops/observability/setup_observability.sh ops/cloudrun/deploy.env
```

Safety controls implemented in scripts:

1. `CONFIRM_PROJECT_ID` must match `PROJECT_ID`.
2. `ALLOW_UPDATE_EXISTING_SERVICE=0` blocks accidental overwrite.
3. Required secrets validated before deploy.
4. Behavioral E2E runs in predeploy gate.

References:

1. `ops/cloudrun/README.md`
2. `docs/passo_a_passo_deploy_anti_burro.md`
3. `docs/roadmap_implantacao_social_agent_cloudrun.md`

## 11. Observability and Operations

Baseline observability includes:

1. Log-based metrics (`social_agent_<service>_*`).
2. Cloud Monitoring dashboard provisioning script.
3. Alert policy templates for errors/DLQ/policy blocks.

Relevant artifacts:

1. `ops/observability/setup_observability.sh`
2. `ops/observability/README.md`
3. `docs/observability_dashboard_spec.md`
4. `docs/runbook_incidentes.md`

## 12. Test Strategy

Test layers:

1. Unit/component tests: connectors, storage, scheduler, policy, webhooks.
2. Integration behavior tests: loop and dispatcher full paths.
3. Behavioral E2E: `tests/test_e2e_agent_behavior.py`.
4. Live LLM E2E (opt-in): `tests/test_e2e_llm.py` with `RUN_E2E_LLM_TESTS=1`.

Quick commands:

```bash
pytest -q tests/test_core.py
pytest -q tests/test_e2e_agent_behavior.py
RUN_E2E_LLM_TESTS=1 pytest -q tests/test_e2e_llm.py
```

## 13. Security and Safety Controls

Implemented controls:

1. Meta webhook signature verification in production.
2. X webhook token authentication.
3. Policy gate before publish/reply.
4. Retry with exponential backoff for transient HTTP errors.
5. Operator queue as safe fallback when automation cannot execute.
6. Prompt-level guardrails disallowing harassment, coercion, threats, deception, and misinformation.

## 14. Known Risks and Current Gaps

1. Policy engine is still MVP-level heuristic and should evolve to richer policy rules.
2. SQLite is local per instance; scale-out needs external durable store (for distributed workers).
3. X full API mode depends on paid API access; operator mode is the no-cost default.
4. Entrypoint consistency must be preserved: deploy/startup should target `src.app.server:fastapi_app` to ensure API + loop are both active.

## 15. Go-Live Checklist

- [ ] Project/region/service name validated (`PROJECT_ID`, `SERVICE_NAME`).
- [ ] Credentials synced to Secret Manager.
- [ ] `predeploy_check.sh` passing.
- [ ] Webhook callbacks configured on platforms.
- [ ] `/health` and webhook smoke tests passing.
- [ ] Dashboard and alerts provisioned.
- [ ] Operator queue workflow validated.
- [ ] Incident runbook owner defined.

## 16. Related Documents

1. `README.md`
2. `docs/passo_a_passo_deploy_anti_burro.md`
3. `docs/conectar_contas_plataformas_anti_burro.md`
4. `docs/x_operacao_sem_api_paga.md`
5. `docs/webhook_contracts.md`
6. `docs/deploy_env_vars.md`
7. `docs/deploy_secrets_matrix.md`
8. `docs/observability_dashboard_spec.md`
9. `docs/runbook_incidentes.md`
