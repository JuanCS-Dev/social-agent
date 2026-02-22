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
- manter `AUTONOMY_ENABLE_GROUNDING=1` e `AUTONOMY_REQUIRE_GROUNDING=1`.
- manter `AGENT_DOMINANT_MODE=1` e ajustar `AGENT_PRIMARY_CTA` para sua campanha.
- para Instagram proativo, preencher `INSTAGRAM_DEFAULT_IMAGE_URL` com uma URL publica de imagem.
- para operar X sem API paga, definir `X_EXECUTION_MODE=operator`.

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
- Meta (Facebook/Instagram)
- X (`X_WEBHOOK_TOKEN` obrigatorio; `X_API_*` opcionais em modo operator)

Guia detalhado de conexao das contas:
- `docs/conectar_contas_plataformas_anti_burro.md`
- `docs/x_operacao_sem_api_paga.md`

Enviar segredos para Secret Manager:

```bash
./ops/cloudrun/sync_secrets.sh ops/cloudrun/deploy.env ops/cloudrun/secrets.env
```

## 4. Gate predeploy (sem deploy)

```bash
./ops/cloudrun/predeploy_check.sh ops/cloudrun/deploy.env
# para incluir E2E live no Vertex:
RUN_LIVE_LLM_E2E=1 ./ops/cloudrun/predeploy_check.sh ops/cloudrun/deploy.env
```

Objetivo:
- validar projeto/alvo/segredos antes de subir revisao.
- rodar E2E comportamental completo localmente.
- opcionalmente validar E2E live do LLM com grounding.

## 5. Deploy do servico

```bash
./ops/cloudrun/deploy.sh ops/cloudrun/deploy.env
```

Observacoes de seguranca:
- se o servico ja existir, o deploy aborta por padrao.
- para atualizar servico existente de proposito, trocar `ALLOW_UPDATE_EXISTING_SERVICE=1`.
- timestamp UTC atual e injetado automaticamente em todos os prompts LLM.

## 6. Configurar webhooks nas plataformas

Depois do deploy, usar URL retornada:
- Reddit trigger: `https://<service-url>/webhooks/reddit`
- X trigger: `https://<service-url>/webhooks/x`
- Meta verify + webhook: `https://<service-url>/webhooks/meta`
- Health: `https://<service-url>/health`
- Fila operador: `https://<service-url>/ops/operator/tasks`

## 7. Ativar observabilidade

```bash
./ops/observability/setup_observability.sh ops/cloudrun/deploy.env
```

Isso cria:
- metricas de log
- dashboard
- alertas basicos

## 8. Smoke test final

```bash
curl -sS https://<service-url>/health
curl -sS -X POST https://<service-url>/webhooks/reddit \
  -H 'content-type: application/json' \
  -d '{"text":"smoke-test"}'
curl -sS -X POST https://<service-url>/webhooks/x \
  -H 'content-type: application/json' \
  -H 'x-social-agent-token: <X_WEBHOOK_TOKEN>' \
  -d '{"tweet_id":"tw_smoke","text":"smoke-test x"}'
```

Resultado esperado:
- health retorna `status=ok`
- webhook retorna `status=accepted`
