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

## X

- [ ] Projeto/app criado no portal
- [ ] Callback URL de staging definido
- [ ] `X_API_KEY` obtido
- [ ] `X_API_SECRET` obtido
- [ ] `X_ACCESS_TOKEN` obtido
- [ ] `X_ACCESS_SECRET` obtido
- [ ] `X_BEARER_TOKEN` (opcional) obtido

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

- [ ] Todos os blocos acima completos
- [ ] `ALLOW_UPDATE_EXISTING_SERVICE=0` confirmado
- [ ] Deploy de staging liberado
