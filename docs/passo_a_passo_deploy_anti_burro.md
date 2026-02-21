# Passo a Passo Anti-Burro (Cloud Run Separado)

Objetivo: subir este projeto em um Cloud Run novo, sem tocar no servico que ja existe em outro projeto.

## 1. Preparar arquivos locais

```bash
cp ops/cloudrun/deploy.env.example ops/cloudrun/deploy.env
cp ops/cloudrun/secrets.env.example ops/cloudrun/secrets.env
```

Editar `ops/cloudrun/deploy.env`:
- `PROJECT_ID`: projeto novo para este agent.
- `CONFIRM_PROJECT_ID`: exatamente igual ao `PROJECT_ID`.
- `SERVICE_NAME`: nome novo de servico (nao reutilizar nome antigo).
- manter `ALLOW_UPDATE_EXISTING_SERVICE=0`.

## 2. Bootstrap de infraestrutura GCP

```bash
./ops/cloudrun/bootstrap_gcp.sh ops/cloudrun/deploy.env
```

Isso cria/valida:
- APIs necessarias
- Artifact Registry
- Service Account runtime + IAM basico

## 3. Preencher credenciais das plataformas

Editar `ops/cloudrun/secrets.env` com:
- Reddit
- X
- Meta (Facebook/Instagram)

Enviar segredos para Secret Manager:

```bash
./ops/cloudrun/sync_secrets.sh ops/cloudrun/deploy.env ops/cloudrun/secrets.env
```

## 4. Deploy do servico

```bash
./ops/cloudrun/deploy.sh ops/cloudrun/deploy.env
```

Observacoes de seguranca:
- se o servico ja existir, o deploy aborta por padrao.
- para atualizar servico existente de proposito, trocar `ALLOW_UPDATE_EXISTING_SERVICE=1`.

## 5. Configurar webhooks nas plataformas

Depois do deploy, usar URL retornada:
- Reddit trigger: `https://<service-url>/webhooks/reddit`
- Meta verify + webhook: `https://<service-url>/webhooks/meta`
- Health: `https://<service-url>/health`

## 6. Ativar observabilidade

```bash
./ops/observability/setup_observability.sh ops/cloudrun/deploy.env
```

Isso cria:
- metricas de log
- dashboard
- alertas basicos

## 7. Smoke test final

```bash
curl -sS https://<service-url>/health
curl -sS -X POST https://<service-url>/webhooks/reddit \
  -H 'content-type: application/json' \
  -d '{"text":"smoke-test"}'
```

Resultado esperado:
- health retorna `status=ok`
- webhook retorna `status=accepted`
