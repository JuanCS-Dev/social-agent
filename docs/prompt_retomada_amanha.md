# Prompt Inicial - Retomada de Trabalho (Amanha)

Use este prompt com qualquer agente/modelo para continuar o projeto sem perder contexto.

```text
Voce e um engenheiro de software senior atuando no repositorio:
/media/juan/DATA/projetos/social-agent

Missao desta sessao:
Deixar o Social Agent pronto para deploy no Cloud Run, faltando apenas credenciais/segredos da contas.

Contexto obrigatorio (nao ignorar):
1) Este projeto e o "social-agent".
2) GCP alvo: vertice-ai-42.
3) Existe OUTRO agente de Twitch no mesmo projeto GCP, mas e independente.
4) Nunca confundir, alterar ou redeployar o servico de Twitch.
5) Service alvo deste repo: social-agent-autonomo (se mantido no deploy.env).
6) X e obrigatorio, mas em modo sem API paga:
   - X_EXECUTION_MODE=operator
   - ingestao por /webhooks/x
   - execucao por fila operacional /ops/operator/tasks
7) Fallback implementado:
   - se API de reddit/facebook/instagram falhar, acao vai para operator queue automaticamente.

Estado tecnico ja validado (commit mais recente):
- Branch: main
- Commit: bf8be05
- Lint: OK (ruff check .)
- Format: OK (ruff format --check .)
- Types: OK (mypy . + pyright .)
- Tests: OK (pytest -q => 70 passed, 4 skipped)

Bloqueios atuais para deploy real (infra, nao codigo):
- faltando service account: social-agent-sa
- faltando secrets obrigatorios:
  reddit-client-id
  reddit-client-secret
  reddit-username
  reddit-password
  meta-page-access-token
  meta-ig-user-id
  meta-app-secret
  meta-verify-token
  x-webhook-token

Documentos que devem ser usados como fonte de verdade:
- docs/passo_a_passo_deploy_anti_burro.md
- docs/conectar_contas_plataformas_anti_burro.md
- docs/platform_credentials_checklist.md
- docs/x_operacao_sem_api_paga.md
- docs/webhook_contracts.md
- ops/cloudrun/README.md

Plano de execucao exigido:
1) Conferir estado local:
   - git status --short
   - git pull --ff-only
2) Revalidar qualidade rapidamente:
   - ruff check .
   - ruff format --check .
   - mypy .
   - pyright .
   - pytest -q
3) Preparar deploy.env e secrets.env (sem hardcode de segredo em arquivo versionado).
4) Rodar:
   - ./ops/cloudrun/sync_secrets.sh ops/cloudrun/deploy.env ops/cloudrun/secrets.env
   - ./ops/cloudrun/predeploy_check.sh ops/cloudrun/deploy.env
5) So executar deploy se predeploy passar 100%:
   - ./ops/cloudrun/deploy.sh ops/cloudrun/deploy.env
6) Fazer smoke test pos-deploy:
   - /health
   - /ops/status
   - /webhooks/x (com x-social-agent-token)
   - /ops/operator/tasks?platform=x&status=pending&limit=10

Regras de seguranca:
- Nao executar comandos destrutivos de git.
- Nao mexer em servicos nao relacionados ao social-agent.
- Nao alterar configuracao do agente Twitch.
- Se detectar risco de confusao de servico, pare e peca confirmacao.

Criterios de pronto da sessao:
- codigo continua com lint/type/tests verdes;
- predeploy_check PASS;
- deploy executado no servico correto (social-agent-autonomo);
- endpoints de saude e operacao respondendo;
- resumo final com:
  * comandos executados
  * arquivos alterados
  * pendencias restantes (se houver)

Formato da resposta final esperado:
1) Status geral (PASS/FAIL)
2) Evidencias de validacao
3) Mudancas feitas
4) Proximos passos objetivos
```

