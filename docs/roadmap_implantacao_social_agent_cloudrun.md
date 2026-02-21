# Roadmap Implementavel: Social Agent -> Cloud Run -> Observabilidade

Data: 2026-02-21  
Objetivo: sair de "MVP local" para "operacao real controlada", com contas de plataformas, deploy no Cloud Run e dashboard operacional.

## 1. Definicao de pronto (Done)

Projeto considerado pronto para operacao quando:
- Webhooks de Meta/Reddit/X chegam no Cloud Run com autenticacao valida.
- Loop autonomo processa eventos sem travar e grava trilha auditavel.
- Deploy e rollback sao reproduziveis via script.
- Dashboard mostra fila, erros, latencia, uso de cota por plataforma.
- Alertas acionam antes de degradacao grave.

## 2. Roadmap em fases (ordem obrigatoria)

## Fase 0 - Preparacao (0.5 dia)

Checklist:
- Confirmar projeto GCP alvo, regiao e owner tecnico.
- Definir ambiente inicial: `staging`.
- Congelar naming padrao:
  - servico: `social-agent`
  - repo de imagem: `social-agent`
  - bucket ops (opcional): `gs://social-agent-ops-<env>`

Entregavel:
- `docs/operational_decisions.md` com nomes finais e responsaveis.

## Fase 1 - Acoes manuais: criacao de contas e apps (1-2 dias)

### 1.1 Reddit
- Criar app OAuth em Reddit Dev Portal.
- Definir redirect URI tecnico.
- Capturar: `reddit_client_id`, `reddit_client_secret`, `reddit_username`, `reddit_password`.
- Validar escopos minimos de operacao.

### 1.2 X
- Criar projeto/app no portal de developer.
- Habilitar OAuth 2.0 + `offline.access` (se refresh necessario).
- Capturar: `x_api_key`, `x_api_secret`, `x_access_token`, `x_access_secret` (ou bearer equivalente).
- Configurar callback URL para ambiente `staging`.

### 1.3 Meta (Facebook + Instagram)
- Criar app no Meta for Developers.
- Conectar Facebook Page e Instagram Professional Account.
- Habilitar produtos/permissions necessarias para post e webhook.
- Capturar: `meta_page_access_token`, `meta_ig_user_id`, `meta_app_secret`, `meta_verify_token`.
- Registrar endpoint de webhook (sera liberado apos deploy de staging).

### 1.4 GCP
- Habilitar APIs:
  - `run.googleapis.com`
  - `artifactregistry.googleapis.com`
  - `cloudbuild.googleapis.com`
  - `secretmanager.googleapis.com`
  - `logging.googleapis.com`
  - `monitoring.googleapis.com`
- Criar Service Account de runtime: `social-agent-sa`.
- Conceder papeis minimos:
  - `roles/secretmanager.secretAccessor`
  - `roles/logging.logWriter`
  - `roles/monitoring.metricWriter`

Entregavel:
- `docs/platform_credentials_checklist.md` preenchido (sem valores secretos).

## Fase 2 - Documentos e artefatos obrigatorios de deploy (1 dia)

Criar no repositorio (obrigatorio):
- `docs/deploy_env_vars.md`
  - lista de env vars, origem (secret/plain), exemplo e descricao.
- `docs/deploy_secrets_matrix.md`
  - segredo -> plataforma -> owner -> rotacao -> criticidade.
- `docs/webhook_contracts.md`
  - endpoint, metodo, validacao de assinatura, payload minimo esperado.
- `docs/runbook_incidentes.md`
  - passos para queda de webhook, rate limit, token expirado, rollback.
- `ops/cloudrun/Dockerfile`
- `ops/cloudrun/cloudbuild.yaml`
- `ops/cloudrun/deploy.sh`

Criterio de aceite:
- qualquer dev consegue subir `staging` seguindo apenas docs acima.

## Fase 3 - Deploy Cloud Run em staging (1 dia)

### 3.1 Build e registry
Comandos base:
```bash
PROJECT_ID=<seu-projeto>
REGION=us-central1
REPO=social-agent
IMAGE=social-agent

gcloud artifacts repositories create $REPO \
  --repository-format=docker --location=$REGION \
  --description="Social Agent images"

gcloud builds submit --tag $REGION-docker.pkg.dev/$PROJECT_ID/$REPO/$IMAGE:staging .
```

### 3.2 Segredos no Secret Manager
```bash
gcloud secrets create reddit-client-id --replication-policy=automatic
gcloud secrets versions add reddit-client-id --data-file=-
# repetir para todos os segredos
```

### 3.3 Deploy do servico
```bash
gcloud run deploy social-agent \
  --image $REGION-docker.pkg.dev/$PROJECT_ID/$REPO/$IMAGE:staging \
  --region $REGION \
  --service-account social-agent-sa@$PROJECT_ID.iam.gserviceaccount.com \
  --allow-unauthenticated \
  --set-env-vars environment=staging,gcp_project=$PROJECT_ID,gcp_location=global \
  --set-secrets reddit_client_id=reddit-client-id:latest
```

### 3.4 Smoke test
```bash
curl -sS https://<URL_DO_CLOUD_RUN>/health
curl -sS -X POST https://<URL_DO_CLOUD_RUN>/webhooks/reddit -H 'content-type: application/json' -d '{"text":"hello"}'
```

Entregavel:
- URL de `staging` online + evidencias de health e webhook.

## Fase 4 - Dashboard de controle e observabilidade (1-2 dias)

## 4.1 Logs estruturados obrigatorios

Padronizar chaves em toda acao:
- `event_id`
- `platform`
- `action_type`
- `policy_decision_id`
- `idempotency_key`
- `status` (`ok`/`error`)
- `error_type`
- `latency_ms`

## 4.2 Metricas operacionais minimas

Criar metricas (logs-based ou custom):
- `events_received_total` (por plataforma)
- `events_processed_total`
- `events_dlq_total`
- `action_failures_total` (por plataforma/acao)
- `policy_block_total`
- `queue_lag_seconds`
- `webhook_signature_failures_total`

## 4.3 Dashboard (Cloud Monitoring)

Widgets minimos:
- Taxa de eventos recebidos/processados (1h, 24h).
- Erros 4xx/5xx por endpoint.
- DLQ growth.
- Latencia p50/p95 por rota.
- Falhas por plataforma (Reddit/X/Meta).
- Consumo de cota estimado por plataforma.

## 4.4 Alertas

Regras iniciais:
- `error_rate > 5%` por 10 min.
- `webhook_signature_failures_total > 0` por 5 min (staging) / >3 (prod).
- `events_dlq_total` crescendo continuamente por 15 min.
- `queue_lag_seconds > 120` por 10 min.
- Sem eventos recebidos por 30 min em horario comercial.

Entregavel:
- `docs/observability_dashboard_spec.md` + links do dashboard e politicas de alerta.

## Fase 5 - Go-live controlado e operacao (0.5-1 dia)

Checklist de virada:
- Deploy `prod` com imagem imutavel (tag+digest).
- Atualizar callback URLs em Reddit/X/Meta para `prod`.
- Rodar smoke tests de `prod`.
- Ativar monitoracao 24h com owner on-call.

Checklist de rollback:
- Manter revisao anterior pronta no Cloud Run.
- Comando rapido:
```bash
gcloud run services update-traffic social-agent --region $REGION --to-revisions <REVISAO_ANTIGA>=100
```

## 3. Plano de execucao sugerido (curto)

Dia 1: Fase 0 + inicio Fase 1  
Dia 2: fechar Fase 1 + Fase 2  
Dia 3: Fase 3 (staging online)  
Dia 4: Fase 4 (dashboard + alertas)  
Dia 5: Fase 5 (go-live controlado)

## 4. Riscos que travam deploy (nao ignorar)

- Token/escopo incompleto nas plataformas.
- Webhook sem validacao de assinatura.
- Secrets em `.env` local sem Secret Manager.
- Sem alerta de DLQ e fila acumulada.
- Deploy sem rollback testado.
