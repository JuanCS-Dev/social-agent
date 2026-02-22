# Checklist de Credenciais de Plataforma

Use este arquivo para controlar status sem expor segredos.

## Ambiente alvo

- Projeto GCP: `__________`
- Regiao: `__________`
- Cloud Run service: `__________`
- Responsavel tecnico: `__________`

## Reddit

- [ ] App OAuth criado
- [ ] Redirect URI definido
- [ ] `REDDIT_CLIENT_ID` obtido
- [ ] `REDDIT_CLIENT_SECRET` obtido
- [ ] `REDDIT_USERNAME` definido
- [ ] `REDDIT_PASSWORD` definido
- [ ] Escopos minimos revisados

## X (obrigatorio na estrategia)

- [ ] `X_EXECUTION_MODE` definido (`operator` sem API paga ou `api`)
- [ ] `X_WEBHOOK_TOKEN` gerado e salvo em segredo
- [ ] Webhook `/webhooks/x` testado com token
- [ ] Se `X_EXECUTION_MODE=api`: `X_ACCESS_TOKEN` obtido

## Meta (Facebook + Instagram)

- [ ] App criado em Meta for Developers
- [ ] Page vinculada
- [ ] Instagram Professional account vinculada
- [ ] `META_PAGE_ACCESS_TOKEN` obtido
- [ ] `META_IG_USER_ID` obtido
- [ ] `META_APP_SECRET` obtido
- [ ] `META_VERIFY_TOKEN` definido
- [ ] Produtos/permissoes revisados

## GCP Secrets

- [ ] `ops/cloudrun/secrets.env` preenchido localmente
- [ ] `./ops/cloudrun/sync_secrets.sh ...` executado
- [ ] Secret Manager validado sem faltas
- [ ] Runtime SA com `secretAccessor`

## Pronto para deploy

- [ ] Reddit + Meta + X prontos
- [ ] `ALLOW_UPDATE_EXISTING_SERVICE=0` confirmado
- [ ] Deploy de staging liberado
