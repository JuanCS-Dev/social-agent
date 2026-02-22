# X Sem API Paga (Modo Operator)

Objetivo: manter X como canal central sem pagar API, com execucao operacional controlada.

## 1) Configurar runtime

Em `ops/cloudrun/deploy.env`:

```bash
X_EXECUTION_MODE=operator
```

Em `ops/cloudrun/secrets.env`:

```bash
X_WEBHOOK_TOKEN=<token-forte>
```

`X_API_*` e `X_ACCESS_*` ficam opcionais nesse modo.

## 2) Subir segredos e deploy

```bash
./ops/cloudrun/sync_secrets.sh ops/cloudrun/deploy.env ops/cloudrun/secrets.env
./ops/cloudrun/predeploy_check.sh ops/cloudrun/deploy.env
./ops/cloudrun/deploy.sh ops/cloudrun/deploy.env
```

## 3) Ingerir sinais do X

Endpoint:
- `POST /webhooks/x`
- Header: `x-social-agent-token: <X_WEBHOOK_TOKEN>`

Exemplo:

```bash
curl -sS -X POST "https://<service-url>/webhooks/x" \
  -H "content-type: application/json" \
  -H "x-social-agent-token: <X_WEBHOOK_TOKEN>" \
  -d '{"tweet_id":"tw_123","text":"mencao recebida"}'
```

## 4) Executar fila operacional

Listar tarefas pendentes:

```bash
curl -sS "https://<service-url>/ops/operator/tasks?platform=x&status=pending&limit=20"
```

Marcar tarefa como concluida:

```bash
curl -sS -X POST "https://<service-url>/ops/operator/tasks/<task_id>/complete" \
  -H "content-type: application/json" \
  -d '{"status":"done","external_id":"tweet_id_real","notes":"executado no perfil web"}'
```

## 5) Fallback para Meta/Reddit (quando API cair)

Ja implementado:
- se chamada API de `reddit`/`facebook`/`instagram` falhar e `OPERATOR_FALLBACK_ON_API_ERROR=1`,
- a acao entra automaticamente na fila `/ops/operator/tasks`.

Uso pratico:
1. Operador abre fila pendente.
2. Executa a acao manualmente no perfil web.
3. Marca `done` com `external_id`.
