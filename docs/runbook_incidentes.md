# Runbook de Incidentes

Escopo: servico deste repositorio, em projeto Cloud Run dedicado.

## 0. Coleta rapida

```bash
PROJECT_ID=<project-id>
REGION=<region>
SERVICE_NAME=<service-name>

gcloud run services describe "$SERVICE_NAME" \
  --project "$PROJECT_ID" --region "$REGION" \
  --format='value(status.url,status.latestReadyRevisionName)'
```

## 1. Deploy falhou

1. Verifique build:

```bash
gcloud builds list --project "$PROJECT_ID" --limit 5
```

2. Verifique imagem:

```bash
gcloud artifacts docker images list "${REGION}-docker.pkg.dev/${PROJECT_ID}/social-agent"
```

3. Reexecute bootstrap e deploy:

```bash
./ops/cloudrun/bootstrap_gcp.sh ops/cloudrun/deploy.env
./ops/cloudrun/deploy.sh ops/cloudrun/deploy.env
```

## 2. `/health` fora do ar

1. Logs recentes:

```bash
gcloud logging read \
  "resource.type=cloud_run_revision AND resource.labels.service_name=${SERVICE_NAME}" \
  --project "$PROJECT_ID" --limit 100 --freshness=30m
```

2. Revisao quebrada: rollback de trafego para ultima revisao estavel.

```bash
gcloud run revisions list \
  --service "$SERVICE_NAME" --region "$REGION" --project "$PROJECT_ID"
```

```bash
gcloud run services update-traffic "$SERVICE_NAME" \
  --region "$REGION" --project "$PROJECT_ID" \
  --to-revisions "<REVISAO_ESTAVEL>=100"
```

## 3. Falha de assinatura Meta (403)

1. Confirmar `ENVIRONMENT=production` em Cloud Run.
2. Confirmar secret `meta-app-secret` atualizado.
3. Confirmar header `X-Hub-Signature-256` enviado pela plataforma.
4. Se precisou trocar segredo, rode:

```bash
./ops/cloudrun/sync_secrets.sh ops/cloudrun/deploy.env ops/cloudrun/secrets.env
./ops/cloudrun/deploy.sh ops/cloudrun/deploy.env
```

## 4. Tokens expirados / rate limit (Reddit/X/Meta)

1. Rotacione o token na plataforma.
2. Atualize `ops/cloudrun/secrets.env`.
3. Rode sync de segredos.
4. Refaça deploy.
5. Valide com smoke test de webhook.

## 5. Crescimento de DLQ

1. Abra dashboard:
   - `Social Agent - <SERVICE_NAME>`
2. Filtre erros por `event_id`.
3. Corrija raiz no conector/policy.
4. Reprocessamento manual:
   - (implementar script de replay quando necessario)
5. Se impacto alto, reduza trafego externo temporariamente.

## 6. Sem eventos recebidos

1. Teste endpoint manualmente.
2. Verifique URL de webhook configurada nas plataformas.
3. Verifique token de verify (Meta) e credenciais.
4. Cheque firewall/proxy do lado da plataforma.

## 7. Escalonamento

Escalar imediatamente se:
- erro continuo > 15 min;
- perda de eventos de producao;
- risco de post indevido por policy.
