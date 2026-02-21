#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOY_ENV_FILE="${1:-${SCRIPT_DIR}/deploy.env}"
SECRETS_ENV_FILE="${2:-${SCRIPT_DIR}/secrets.env}"

if [[ ! -f "${DEPLOY_ENV_FILE}" ]]; then
  echo "Missing deploy env file: ${DEPLOY_ENV_FILE}"
  exit 1
fi

if [[ ! -f "${SECRETS_ENV_FILE}" ]]; then
  echo "Missing secrets env file: ${SECRETS_ENV_FILE}"
  echo "Copy template: cp ${SCRIPT_DIR}/secrets.env.example ${SCRIPT_DIR}/secrets.env"
  exit 1
fi

if ! command -v gcloud >/dev/null 2>&1; then
  echo "gcloud CLI not found."
  exit 1
fi

set -a
source "${DEPLOY_ENV_FILE}"
source "${SECRETS_ENV_FILE}"
set +a

: "${PROJECT_ID:?PROJECT_ID is required in deploy env}"
: "${CONFIRM_PROJECT_ID:?CONFIRM_PROJECT_ID is required in deploy env}"

if [[ "${PROJECT_ID}" != "${CONFIRM_PROJECT_ID}" ]]; then
  echo "Safety stop: CONFIRM_PROJECT_ID must match PROJECT_ID."
  echo "PROJECT_ID=${PROJECT_ID}"
  echo "CONFIRM_PROJECT_ID=${CONFIRM_PROJECT_ID}"
  exit 1
fi

SERVICE_ACCOUNT_NAME="${SERVICE_ACCOUNT_NAME:-social-agent-sa}"
SERVICE_ACCOUNT_EMAIL="${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

ACTIVE_ACCOUNT="$(gcloud auth list --filter=status:ACTIVE --format='value(account)' | head -n1 || true)"
if [[ -z "${ACTIVE_ACCOUNT}" ]]; then
  echo "No active gcloud account. Run: gcloud auth login"
  exit 1
fi

required_vars=(
  REDDIT_CLIENT_ID
  REDDIT_CLIENT_SECRET
  REDDIT_USERNAME
  REDDIT_PASSWORD
  X_API_KEY
  X_API_SECRET
  X_ACCESS_TOKEN
  X_ACCESS_SECRET
  META_PAGE_ACCESS_TOKEN
  META_IG_USER_ID
  META_APP_SECRET
  META_VERIFY_TOKEN
)

optional_vars=(
  X_BEARER_TOKEN
)

missing=()
for var_name in "${required_vars[@]}"; do
  if [[ -z "${!var_name:-}" ]]; then
    missing+=("${var_name}")
  fi
done

if (( ${#missing[@]} > 0 )); then
  echo "Missing required secret values:"
  printf ' - %s\n' "${missing[@]}"
  exit 1
fi

to_secret_name() {
  local var_name="$1"
  echo "${var_name,,}" | tr '_' '-'
}

upsert_secret() {
  local secret_name="$1"
  local secret_value="$2"

  if gcloud secrets describe "${secret_name}" --project "${PROJECT_ID}" >/dev/null 2>&1; then
    printf "%s" "${secret_value}" | gcloud secrets versions add "${secret_name}" \
      --data-file=- \
      --project "${PROJECT_ID}" >/dev/null
    echo "Updated secret: ${secret_name}"
  else
    gcloud secrets create "${secret_name}" \
      --replication-policy=automatic \
      --project "${PROJECT_ID}" >/dev/null
    printf "%s" "${secret_value}" | gcloud secrets versions add "${secret_name}" \
      --data-file=- \
      --project "${PROJECT_ID}" >/dev/null
    echo "Created secret: ${secret_name}"
  fi

  gcloud secrets add-iam-policy-binding "${secret_name}" \
    --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
    --role="roles/secretmanager.secretAccessor" \
    --project "${PROJECT_ID}" \
    --quiet >/dev/null
}

echo "Syncing required secrets to project ${PROJECT_ID}..."
for var_name in "${required_vars[@]}"; do
  upsert_secret "$(to_secret_name "${var_name}")" "${!var_name}"
done

echo "Syncing optional secrets when provided..."
for var_name in "${optional_vars[@]}"; do
  if [[ -n "${!var_name:-}" ]]; then
    upsert_secret "$(to_secret_name "${var_name}")" "${!var_name}"
  else
    echo "Skipping optional empty secret: ${var_name}"
  fi
done

echo "Secrets sync complete."
