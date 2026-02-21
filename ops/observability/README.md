# Observability Ops

Provisiona metricas, dashboard e alertas baseline para o service alvo.

Comando:

```bash
./ops/observability/setup_observability.sh ops/cloudrun/deploy.env
```

Pre-requisitos:
- deploy ja realizado
- logs chegando no Cloud Logging
- permissao de Monitoring no projeto alvo
