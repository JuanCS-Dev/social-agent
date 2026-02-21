# Deploy Secrets Matrix

Arquivo local de entrada: `ops/cloudrun/secrets.env`  
Destino final: Secret Manager (`gcloud secrets`)

## Matriz

| Env var local | Secret Manager | Plataforma | Dono | Rotacao | Criticidade |
| --- | --- | --- | --- | --- | --- |
| `REDDIT_CLIENT_ID` | `reddit-client-id` | Reddit | Owner integracao Reddit | 180 dias | Alta |
| `REDDIT_CLIENT_SECRET` | `reddit-client-secret` | Reddit | Owner integracao Reddit | 90 dias | Critica |
| `REDDIT_USERNAME` | `reddit-username` | Reddit | Owner integracao Reddit | quando trocar conta | Media |
| `REDDIT_PASSWORD` | `reddit-password` | Reddit | Owner integracao Reddit | 90 dias | Critica |
| `X_API_KEY` | `x-api-key` | X | Owner integracao X | 180 dias | Alta |
| `X_API_SECRET` | `x-api-secret` | X | Owner integracao X | 90 dias | Critica |
| `X_ACCESS_TOKEN` | `x-access-token` | X | Owner integracao X | 90 dias | Critica |
| `X_ACCESS_SECRET` | `x-access-secret` | X | Owner integracao X | 90 dias | Critica |
| `X_BEARER_TOKEN` | `x-bearer-token` | X | Owner integracao X | 90 dias | Alta |
| `META_PAGE_ACCESS_TOKEN` | `meta-page-access-token` | Meta | Owner integracao Meta | 60 dias | Critica |
| `META_IG_USER_ID` | `meta-ig-user-id` | Meta | Owner integracao Meta | fixo por conta | Media |
| `META_APP_SECRET` | `meta-app-secret` | Meta | Owner integracao Meta | 90 dias | Critica |
| `META_VERIFY_TOKEN` | `meta-verify-token` | Meta | Owner integracao Meta | 180 dias | Alta |

## Fluxo anti-erro

1. Preencher `ops/cloudrun/secrets.env` localmente (nao commitar).
2. Rodar:

```bash
./ops/cloudrun/sync_secrets.sh ops/cloudrun/deploy.env ops/cloudrun/secrets.env
```

3. Validar se todos existem:

```bash
for s in \
  reddit-client-id reddit-client-secret reddit-username reddit-password \
  x-api-key x-api-secret x-access-token x-access-secret \
  meta-page-access-token meta-ig-user-id meta-app-secret meta-verify-token
do
  gcloud secrets describe "$s" --project "$(grep '^PROJECT_ID=' ops/cloudrun/deploy.env | cut -d= -f2-)" >/dev/null \
    && echo "ok: $s" || echo "missing: $s"
done
```
