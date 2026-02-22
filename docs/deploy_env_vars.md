# Deploy Env Vars (Cloud Run Separado)

Objetivo: configurar este agent em um projeto Cloud Run novo, sem tocar no servico ja existente em outro projeto.

Arquivo alvo: `ops/cloudrun/deploy.env`

## Variaveis obrigatorias

| Variavel | Tipo | Origem | Exemplo | Uso |
| --- | --- | --- | --- | --- |
| `PROJECT_ID` | plain | manual | `social-agent-staging-123` | Projeto GCP alvo deste deploy |
| `CONFIRM_PROJECT_ID` | plain | manual | `social-agent-staging-123` | Trava de seguranca: deve ser igual ao `PROJECT_ID` |
| `REGION` | plain | manual | `us-central1` | Regiao Cloud Run e Artifact Registry |
| `SERVICE_NAME` | plain | manual | `social-agent-autonomo` | Nome do novo servico Cloud Run |
| `SERVICE_ACCOUNT_NAME` | plain | manual | `social-agent-sa` | Nome da service account runtime |

## Variaveis de imagem/build

| Variavel | Tipo | Default sugerido | Uso |
| --- | --- | --- | --- |
| `ARTIFACT_REPO` | plain | `social-agent` | Repo Docker no Artifact Registry |
| `IMAGE_NAME` | plain | `social-agent` | Nome da imagem |
| `IMAGE_TAG` | plain | `staging` | Tag da imagem |

## Variaveis de runtime

| Variavel | Tipo | Default sugerido | Uso |
| --- | --- | --- | --- |
| `ENVIRONMENT` | plain | `staging` | Modo de ambiente da app |
| `GCP_LOCATION` | plain | `global` | Local usado pelo Vertex AI |
| `DATABASE_URL` | plain | `sqlite+aiosqlite:////tmp/social_agent.db` | Banco local efemero no container |
| `REDDIT_USER_AGENT` | plain | `ByteSocialAgent/1.0.0` | User-Agent do conector Reddit |
| `AUTONOMY_POLL_SECONDS` | plain | `5` | Intervalo do loop autonomo |
| `AUTONOMY_ENABLE_PROACTIVE` | `0/1` | `1` | Liga ciclo proativo de publicacao |
| `AUTONOMY_USE_LLM_GENERATION` | `0/1` | `1` | Liga geracao por Gemini |
| `AUTONOMY_MAX_PROACTIVE_ACTIONS_PER_TICK` | plain | `1` | Limite por ciclo proativo |
| `AUTONOMY_ENABLE_GROUNDING` | `0/1` | `1` | Ativa ferramenta de grounding (Google Search) no Gemini |
| `AUTONOMY_REQUIRE_GROUNDING` | `0/1` | `1` | Exige metadata de grounding; sem isso cai para fallback seguro |
| `AUTONOMY_DEFAULT_LANGUAGE` | plain | `pt` | Idioma default para conteudo proativo |
| `AGENT_GOAL` | plain | texto default | Objetivo editorial do agent |
| `AGENT_IDEOLOGY` | plain | texto default | Direcao ideologica configuravel |
| `AGENT_MORAL_FRAMEWORK` | plain | texto default | Limites morais de resposta/publicacao |
| `AGENT_DOMINANT_MODE` | `0/1` | `1` | Ativa tom dominante com foco em crescimento de audiencia |
| `AGENT_PRIMARY_CTA` | plain | texto default | CTA padrao para conversao de audiencia |
| `AGENT_GROWTH_KPI_PRIORITIES` | plain | `reach,share_rate,follow_conversion,retention` | KPIs priorizados para reflexao diaria e execucao |
| `INSTAGRAM_DEFAULT_IMAGE_URL` | plain | vazio | URL padrao de imagem para publicacao Instagram |
| `X_EXECUTION_MODE` | plain | `operator` | `operator` usa fila operacional sem API paga; `api` usa credenciais X |

## Variaveis de capacidade

| Variavel | Tipo | Default sugerido | Uso |
| --- | --- | --- | --- |
| `CPU` | plain | `1` | CPU por instancia |
| `MEMORY` | plain | `512Mi` | Memoria por instancia |
| `MIN_INSTANCES` | plain | `0` | Instancias minimas |
| `MAX_INSTANCES` | plain | `3` | Instancias maximas |
| `TIMEOUT_SECONDS` | plain | `300` | Timeout de request |

## Trava de seguranca de deploy

| Variavel | Tipo | Default sugerido | Uso |
| --- | --- | --- | --- |
| `ALLOW_UPDATE_EXISTING_SERVICE` | plain | `0` | Com `0`, aborta se o servico ja existir |

## Regras praticas

1. Nunca coloque credenciais em `deploy.env`.
2. Credenciais vao somente em `ops/cloudrun/secrets.env` e Secret Manager.
3. `X_EXECUTION_MODE=operator` e o caminho sem custo para manter X ativo na estrategia.
4. Com `X_EXECUTION_MODE=operator`, manter `X_WEBHOOK_TOKEN` definido em Secret Manager.
5. Com `X_EXECUTION_MODE=api`, `x-access-token` vira obrigatorio.
6. Para Instagram proativo, defina `INSTAGRAM_DEFAULT_IMAGE_URL` com URL publica valida.
7. Mantenha `ALLOW_UPDATE_EXISTING_SERVICE=0` ate confirmar o alvo.
6. Antes de deploy, valide:

```bash
grep -E '^(PROJECT_ID|CONFIRM_PROJECT_ID|REGION|SERVICE_NAME|SERVICE_ACCOUNT_NAME)=' ops/cloudrun/deploy.env
./ops/cloudrun/predeploy_check.sh ops/cloudrun/deploy.env
```

7. Para rodar validacao live do LLM no gate predeploy:

```bash
RUN_LIVE_LLM_E2E=1 ./ops/cloudrun/predeploy_check.sh ops/cloudrun/deploy.env
```

## Grounding + Timestamp (anti-desatualizacao)

1. `AUTONOMY_ENABLE_GROUNDING=1` liga o `google_search` em todas as chamadas LLM.
2. `AUTONOMY_REQUIRE_GROUNDING=1` obriga retorno com metadata de grounding.
3. O agent injeta `Current UTC timestamp: <iso8601>` em todos os prompts LLM.
4. Com isso, o modelo recebe referencia temporal explicita de runtime e reduz respostas ancoradas no tempo de treino.
