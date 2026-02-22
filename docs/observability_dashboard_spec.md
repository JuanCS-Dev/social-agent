# Observability Dashboard Spec

Objetivo: monitorar saude operacional do social agent em Cloud Run.

## Provisionamento automatico

Script:

```bash
./ops/observability/setup_observability.sh ops/cloudrun/deploy.env
```

Ele cria/atualiza:
- metricas de log com prefixo `social_agent_<service_slug>_*`
- dashboard `Social Agent - <SERVICE_NAME>`
- alertas baseline (quando `gcloud alpha monitoring policies` estiver disponivel)

## Metricas criadas

- `social_agent_<service_slug>_events_received`
- `social_agent_<service_slug>_reddit_webhooks`
- `social_agent_<service_slug>_meta_webhooks`
- `social_agent_<service_slug>_errors`
- `social_agent_<service_slug>_dlq_events`
- `social_agent_<service_slug>_policy_blocks`
- `social_agent_<service_slug>_proactive_actions`
- `social_agent_<service_slug>_daily_reflections`

## Widgets minimos do dashboard

1. Taxa de eventos recebidos (line chart, align rate 60s)
2. Erros por minuto (line chart, align sum 60s)
3. Eventos em DLQ (bar chart, align sum 60s)
4. Bloqueios de policy (bar chart, align sum 60s)
5. Acoes proativas por minuto (line chart, align sum 60s)
6. Reflexoes diarias (line chart, align sum 60s)

## Alertas baseline

1. Error burst: erros > 5 em 5 min
2. DLQ growth: DLQ > 3 em 5 min
3. Policy blocks high: bloqueios > 5 em 5 min

## Criterio de aceite

1. Dashboard visivel no projeto correto.
2. Metricas atualizando apos smoke test.
3. Pelo menos 1 alerta de teste disparado e fechado.
