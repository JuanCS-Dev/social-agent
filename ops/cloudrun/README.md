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

4. Deploy:

```bash
./ops/cloudrun/deploy.sh ops/cloudrun/deploy.env
```

Notas:
- `ALLOW_UPDATE_EXISTING_SERVICE=0` bloqueia update acidental.
- Use `CONFIRM_PROJECT_ID` para evitar deploy no projeto errado.
