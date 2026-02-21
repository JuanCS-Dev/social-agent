# Operational Decisions

Documento para congelar decisoes de operacao antes do go-live.

## Identidade do deployment

- Projeto GCP alvo: `__________`
- Regiao: `__________`
- Service name: `__________`
- Service account runtime: `__________`
- Ambiente atual: `staging` | `production`

## Guardrails

- [ ] Projeto deste agent separado do outro bot em Cloud Run
- [ ] `ALLOW_UPDATE_EXISTING_SERVICE=0` por padrao
- [ ] `CONFIRM_PROJECT_ID == PROJECT_ID`

## Responsaveis

- Owner tecnico: `__________`
- Owner de credenciais: `__________`
- Owner de observabilidade/on-call: `__________`

## SLO inicial

- Disponibilidade endpoint `/health`: `____%`
- Latencia p95 webhook: `____ ms`
- Taxa maxima de erro 5xx: `____%`
- Tempo maximo para responder incidente P1: `____ min`

## Datas

- Data de freeze de configuracao: `____/____/______`
- Data de go-live: `____/____/______`
