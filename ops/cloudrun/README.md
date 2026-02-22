# Cloud Run Ops

Fluxo recomendado:

1. Copiar templates:

```bash
cp ops/cloudrun/deploy.env.example ops/cloudrun/deploy.env
cp ops/cloudrun/secrets.env.example ops/cloudrun/secrets.env
```

2. Bootstrap GCP:

```bash
./ops/cloudrun/bootstrap_gcp.sh ops/cloudrun/deploy.env
```

3. Sincronizar segredos:

```bash
./ops/cloudrun/sync_secrets.sh ops/cloudrun/deploy.env ops/cloudrun/secrets.env
```

4. Gate predeploy (sem subir servico):

```bash
./ops/cloudrun/predeploy_check.sh ops/cloudrun/deploy.env
# opcional live LLM E2E:
RUN_LIVE_LLM_E2E=1 ./ops/cloudrun/predeploy_check.sh ops/cloudrun/deploy.env
```

5. Deploy:

```bash
./ops/cloudrun/deploy.sh ops/cloudrun/deploy.env
```

Notas:
- `ALLOW_UPDATE_EXISTING_SERVICE=0` bloqueia update acidental.
- Use `CONFIRM_PROJECT_ID` para evitar deploy no projeto errado.
- `X_WEBHOOK_TOKEN` e obrigatorio para ingestao segura no endpoint `/webhooks/x`.
- Segredos `X_API_*`/`X_ACCESS_*` sao opcionais quando `X_EXECUTION_MODE=operator`.
