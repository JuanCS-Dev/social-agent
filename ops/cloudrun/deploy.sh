#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
DEPLOY_ENV_FILE="${1:-${SCRIPT_DIR}/deploy.env}"

if [[ ! -f "${DEPLOY_ENV_FILE}" ]]; then
  echo "Missing deploy env file: ${DEPLOY_ENV_FILE}"
  echo "Copy template: cp ${SCRIPT_DIR}/deploy.env.example ${SCRIPT_DIR}/deploy.env"
  exit 1
fi

if ! command -v gcloud >/dev/null 2>&1; then
  echo "gcloud CLI not found."
  exit 1
fi

set -a
source "${DEPLOY_ENV_FILE}"
set +a

: "${PROJECT_ID:?PROJECT_ID is required in deploy env}"
: "${CONFIRM_PROJECT_ID:?CONFIRM_PROJECT_ID is required in deploy env}"
: "${SERVICE_NAME:?SERVICE_NAME is required in deploy env}"

if [[ "${PROJECT_ID}" != "${CONFIRM_PROJECT_ID}" ]]; then
  echo "Safety stop: CONFIRM_PROJECT_ID must match PROJECT_ID."
  echo "PROJECT_ID=${PROJECT_ID}"
  echo "CONFIRM_PROJECT_ID=${CONFIRM_PROJECT_ID}"
  exit 1
fi

REGION="${REGION:-us-central1}"
ARTIFACT_REPO="${ARTIFACT_REPO:-social-agent}"
IMAGE_NAME="${IMAGE_NAME:-social-agent}"
IMAGE_TAG="${IMAGE_TAG:-staging}"
ENVIRONMENT="${ENVIRONMENT:-staging}"
GCP_LOCATION="${GCP_LOCATION:-global}"
DATABASE_URL="${DATABASE_URL:-sqlite+aiosqlite:////tmp/social_agent.db}"
REDDIT_USER_AGENT="${REDDIT_USER_AGENT:-ByteSocialAgent/1.0.0}"
AUTONOMY_POLL_SECONDS="${AUTONOMY_POLL_SECONDS:-5}"
AUTONOMY_ENABLE_PROACTIVE="${AUTONOMY_ENABLE_PROACTIVE:-1}"
AUTONOMY_USE_LLM_GENERATION="${AUTONOMY_USE_LLM_GENERATION:-1}"
AUTONOMY_MAX_PROACTIVE_ACTIONS_PER_TICK="${AUTONOMY_MAX_PROACTIVE_ACTIONS_PER_TICK:-1}"
AUTONOMY_ENABLE_GROUNDING="${AUTONOMY_ENABLE_GROUNDING:-1}"
AUTONOMY_REQUIRE_GROUNDING="${AUTONOMY_REQUIRE_GROUNDING:-1}"
AUTONOMY_DEFAULT_LANGUAGE="${AUTONOMY_DEFAULT_LANGUAGE:-pt}"
AGENT_GOAL="${AGENT_GOAL:-Construir audiencia de alta lealdade e crescer alcance com conteudo de alta conviccao.}"
AGENT_IDEOLOGY="${AGENT_IDEOLOGY:-Lideranca forte, responsabilidade individual, liberdade economica, disciplina e resultado.}"
AGENT_MORAL_FRAMEWORK="${AGENT_MORAL_FRAMEWORK:-Sem coercao, sem assedio, sem desinformacao, sem manipulacao predatoria.}"
AGENT_DOMINANT_MODE="${AGENT_DOMINANT_MODE:-1}"
AGENT_PRIMARY_CTA="${AGENT_PRIMARY_CTA:-Siga e ative notificacoes para acompanhar os proximos movimentos.}"
AGENT_GROWTH_KPI_PRIORITIES="${AGENT_GROWTH_KPI_PRIORITIES:-reach,share_rate,follow_conversion,retention}"
INSTAGRAM_DEFAULT_IMAGE_URL="${INSTAGRAM_DEFAULT_IMAGE_URL:-}"
X_EXECUTION_MODE="${X_EXECUTION_MODE:-operator}"
OPERATOR_FALLBACK_ON_API_ERROR="${OPERATOR_FALLBACK_ON_API_ERROR:-1}"
SERVICE_ACCOUNT_NAME="${SERVICE_ACCOUNT_NAME:-social-agent-sa}"
SERVICE_ACCOUNT_EMAIL="${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
ALLOW_UPDATE_EXISTING_SERVICE="${ALLOW_UPDATE_EXISTING_SERVICE:-0}"
CPU="${CPU:-1}"
MEMORY="${MEMORY:-512Mi}"
MIN_INSTANCES="${MIN_INSTANCES:-0}"
MAX_INSTANCES="${MAX_INSTANCES:-3}"
TIMEOUT_SECONDS="${TIMEOUT_SECONDS:-300}"

if [[ "${X_EXECUTION_MODE}" != "api" && "${X_EXECUTION_MODE}" != "operator" ]]; then
  echo "Invalid X_EXECUTION_MODE: ${X_EXECUTION_MODE} (use api|operator)"
  exit 1
fi

ACTIVE_ACCOUNT="$(gcloud auth list --filter=status:ACTIVE --format='value(account)' | head -n1 || true)"
if [[ -z "${ACTIVE_ACCOUNT}" ]]; then
  echo "No active gcloud account. Run: gcloud auth login"
  exit 1
fi

echo "Using gcloud account: ${ACTIVE_ACCOUNT}"
echo "Target project/region/service: ${PROJECT_ID}/${REGION}/${SERVICE_NAME}"

if ! gcloud iam service-accounts describe "${SERVICE_ACCOUNT_EMAIL}" --project "${PROJECT_ID}" >/dev/null 2>&1; then
  echo "Missing runtime service account: ${SERVICE_ACCOUNT_EMAIL}"
  echo "Run bootstrap first: ${SCRIPT_DIR}/bootstrap_gcp.sh ${DEPLOY_ENV_FILE}"
  exit 1
fi

if gcloud run services describe "${SERVICE_NAME}" --region "${REGION}" --project "${PROJECT_ID}" >/dev/null 2>&1; then
  if [[ "${ALLOW_UPDATE_EXISTING_SERVICE}" != "1" ]]; then
    echo "Safety stop: Cloud Run service '${SERVICE_NAME}' already exists in ${PROJECT_ID}/${REGION}."
    echo "To update this existing service intentionally, set ALLOW_UPDATE_EXISTING_SERVICE=1 in deploy.env."
    exit 1
  fi
  echo "Existing service detected and explicit update allowed."
else
  echo "Deploy target is a new service: ${SERVICE_NAME}"
fi

required_secret_bindings=(
  REDDIT_CLIENT_ID=reddit-client-id:latest
  REDDIT_CLIENT_SECRET=reddit-client-secret:latest
  REDDIT_USERNAME=reddit-username:latest
  REDDIT_PASSWORD=reddit-password:latest
  META_PAGE_ACCESS_TOKEN=meta-page-access-token:latest
  META_IG_USER_ID=meta-ig-user-id:latest
  META_APP_SECRET=meta-app-secret:latest
  META_VERIFY_TOKEN=meta-verify-token:latest
  X_WEBHOOK_TOKEN=x-webhook-token:latest
)

optional_secret_bindings=(
  X_API_KEY=x-api-key:latest
  X_API_SECRET=x-api-secret:latest
  X_ACCESS_TOKEN=x-access-token:latest
  X_ACCESS_SECRET=x-access-secret:latest
  X_BEARER_TOKEN=x-bearer-token:latest
)

binding_secret_name() {
  local binding="$1"
  echo "${binding#*=}" | cut -d: -f1
}

missing_secrets=()
for binding in "${required_secret_bindings[@]}"; do
  secret_name="$(binding_secret_name "${binding}")"
  if ! gcloud secrets describe "${secret_name}" --project "${PROJECT_ID}" >/dev/null 2>&1; then
    missing_secrets+=("${secret_name}")
  fi
done

if (( ${#missing_secrets[@]} > 0 )); then
  echo "Missing required secrets in Secret Manager:"
  printf ' - %s\n' "${missing_secrets[@]}"
  echo "Run: ${SCRIPT_DIR}/sync_secrets.sh ${DEPLOY_ENV_FILE} ${SCRIPT_DIR}/secrets.env"
  exit 1
fi

secret_bindings=("${required_secret_bindings[@]}")
for binding in "${optional_secret_bindings[@]}"; do
  secret_name="$(binding_secret_name "${binding}")"
  if gcloud secrets describe "${secret_name}" --project "${PROJECT_ID}" >/dev/null 2>&1; then
    secret_bindings+=("${binding}")
  else
    echo "Skipping optional secret not found: ${secret_name}"
  fi
done

IMAGE_URI="${REGION}-docker.pkg.dev/${PROJECT_ID}/${ARTIFACT_REPO}/${IMAGE_NAME}:${IMAGE_TAG}"

echo "Building image via Cloud Build: ${IMAGE_URI}"
gcloud builds submit "${REPO_ROOT}" \
  --project "${PROJECT_ID}" \
  --config "${SCRIPT_DIR}/cloudbuild.yaml" \
  --substitutions "_REGION=${REGION},_REPO=${ARTIFACT_REPO},_IMAGE=${IMAGE_NAME},_TAG=${IMAGE_TAG}"

env_vars=(
  ENVIRONMENT="${ENVIRONMENT}"
  GCP_PROJECT="${PROJECT_ID}"
  GCP_LOCATION="${GCP_LOCATION}"
  DATABASE_URL="${DATABASE_URL}"
  REDDIT_USER_AGENT="${REDDIT_USER_AGENT}"
  AUTONOMY_POLL_SECONDS="${AUTONOMY_POLL_SECONDS}"
  AUTONOMY_ENABLE_PROACTIVE="${AUTONOMY_ENABLE_PROACTIVE}"
  AUTONOMY_USE_LLM_GENERATION="${AUTONOMY_USE_LLM_GENERATION}"
  AUTONOMY_MAX_PROACTIVE_ACTIONS_PER_TICK="${AUTONOMY_MAX_PROACTIVE_ACTIONS_PER_TICK}"
  AUTONOMY_ENABLE_GROUNDING="${AUTONOMY_ENABLE_GROUNDING}"
  AUTONOMY_REQUIRE_GROUNDING="${AUTONOMY_REQUIRE_GROUNDING}"
  AUTONOMY_DEFAULT_LANGUAGE="${AUTONOMY_DEFAULT_LANGUAGE}"
  AGENT_GOAL="${AGENT_GOAL}"
  AGENT_IDEOLOGY="${AGENT_IDEOLOGY}"
  AGENT_MORAL_FRAMEWORK="${AGENT_MORAL_FRAMEWORK}"
  AGENT_DOMINANT_MODE="${AGENT_DOMINANT_MODE}"
  AGENT_PRIMARY_CTA="${AGENT_PRIMARY_CTA}"
  AGENT_GROWTH_KPI_PRIORITIES="${AGENT_GROWTH_KPI_PRIORITIES}"
  INSTAGRAM_DEFAULT_IMAGE_URL="${INSTAGRAM_DEFAULT_IMAGE_URL}"
  X_EXECUTION_MODE="${X_EXECUTION_MODE}"
  OPERATOR_FALLBACK_ON_API_ERROR="${OPERATOR_FALLBACK_ON_API_ERROR}"
)

ENV_VARS_ARG="$(IFS=,; echo "${env_vars[*]}")"
SECRETS_ARG="$(IFS=,; echo "${secret_bindings[*]}")"
LABELS_ARG="app=social-agent,managed-by=script,environment=${ENVIRONMENT}"

echo "Deploying Cloud Run service: ${SERVICE_NAME}"
gcloud run deploy "${SERVICE_NAME}" \
  --project "${PROJECT_ID}" \
  --region "${REGION}" \
  --image "${IMAGE_URI}" \
  --service-account "${SERVICE_ACCOUNT_EMAIL}" \
  --allow-unauthenticated \
  --cpu "${CPU}" \
  --memory "${MEMORY}" \
  --min-instances "${MIN_INSTANCES}" \
  --max-instances "${MAX_INSTANCES}" \
  --timeout "${TIMEOUT_SECONDS}s" \
  --labels "${LABELS_ARG}" \
  --set-env-vars "${ENV_VARS_ARG}" \
  --set-secrets "${SECRETS_ARG}"

SERVICE_URL="$(gcloud run services describe "${SERVICE_NAME}" --project "${PROJECT_ID}" --region "${REGION}" --format='value(status.url)')"

echo "Deploy complete."
echo "Service URL: ${SERVICE_URL}"
echo "Health check: ${SERVICE_URL}/health"
echo "Webhook Reddit: ${SERVICE_URL}/webhooks/reddit"
echo "Webhook X: ${SERVICE_URL}/webhooks/x"
echo "Webhook Meta verify: ${SERVICE_URL}/webhooks/meta"
echo "Operator queue: ${SERVICE_URL}/ops/operator/tasks"
