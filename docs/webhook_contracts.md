# Webhook Contracts

Base URL: `https://<cloud-run-url>`

## 1) Reddit

- Endpoint: `POST /webhooks/reddit`
- Auth: sem assinatura obrigatoria no codigo atual.
- Content-Type: `application/json`
- Payload minimo esperado:

```json
{
  "text": "mensagem de teste"
}
```

- Resposta de sucesso (`200`):

```json
{
  "status": "accepted",
  "event_id": "evt_rdt_xxxxxxxxxx"
}
```

## 2) X event ingest

- Endpoint: `POST /webhooks/x`
- Auth:
  - Header opcional no protocolo, mas recomendado no deploy: `X-Social-Agent-Token: <X_WEBHOOK_TOKEN>`.
  - Se `X_WEBHOOK_TOKEN` estiver definido no runtime e header nao bater, retorna `403`.
- Content-Type: `application/json`
- Payload minimo esperado:

```json
{
  "tweet_id": "tw_123",
  "text": "mencao recebida"
}
```

- Resposta de sucesso (`200`):

```json
{
  "status": "accepted",
  "event_id": "evt_x_xxxxxxxxxx"
}
```

## 3) Meta webhook event

- Endpoint: `POST /webhooks/meta`
- Auth:
  - `ENVIRONMENT=production`: assinatura `X-Hub-Signature-256` obrigatoria.
  - `ENVIRONMENT!=production`: assinatura nao bloqueia request.
- Content-Type: `application/json`
- Resposta de sucesso (`200`):

```json
{
  "status": "accepted",
  "event_id": "evt_mta_xxxxxxxxxx"
}
```

- Falha de assinatura em producao: `403`.

## 4) Meta webhook verification

- Endpoint: `GET /webhooks/meta`
- Query params obrigatorios:
  - `hub.mode=subscribe`
  - `hub.verify_token=<META_VERIFY_TOKEN>`
  - `hub.challenge=<numero>`
- Sucesso: retorna o `hub.challenge` como inteiro.
- Falhas:
  - token invalido: `403`
  - parametros faltando: `400`

## Smoke tests

```bash
curl -sS "${SERVICE_URL}/health"

curl -sS -X POST "${SERVICE_URL}/webhooks/reddit" \
  -H 'content-type: application/json' \
  -d '{"text":"smoke from runbook"}'

curl -sS -X POST "${SERVICE_URL}/webhooks/x" \
  -H 'content-type: application/json' \
  -H 'x-social-agent-token: <X_WEBHOOK_TOKEN>' \
  -d '{"tweet_id":"tw_1","text":"smoke x"}'

curl -sS "${SERVICE_URL}/webhooks/meta?hub.mode=subscribe&hub.verify_token=<TOKEN>&hub.challenge=12345"
```
