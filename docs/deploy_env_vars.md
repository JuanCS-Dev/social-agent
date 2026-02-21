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
3. Mantenha `ALLOW_UPDATE_EXISTING_SERVICE=0` ate confirmar o alvo.
4. Antes de deploy, valide:

```bash
grep -E '^(PROJECT_ID|CONFIRM_PROJECT_ID|REGION|SERVICE_NAME|SERVICE_ACCOUNT_NAME)=' ops/cloudrun/deploy.env
```
