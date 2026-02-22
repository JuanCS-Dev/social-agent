#!/usr/bin/env bash
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOY_ENV_FILE="${1:-${SCRIPT_DIR}/deploy.env}"
RUN_LIVE_LLM_E2E="${RUN_LIVE_LLM_E2E:-0}"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

if [[ ! -f "${DEPLOY_ENV_FILE}" ]]; then
  echo "Missing deploy env file: ${DEPLOY_ENV_FILE}"
  echo "Copy template: cp ${SCRIPT_DIR}/deploy.env.example ${SCRIPT_DIR}/deploy.env"
  exit 1
fi

set -a
source "${DEPLOY_ENV_FILE}"
set +a

failures=()
warnings=()

record_failure() {
  local check_name="$1"
  failures+=("${check_name}")
  echo "[FAIL] ${check_name}"
}

record_ok() {
  local check_name="$1"
  echo "[OK] ${check_name}"
}

record_warn() {
  local check_name="$1"
  warnings+=("${check_name}")
  echo "[WARN] ${check_name}"
}

check_cmd() {
  local check_name="$1"
  shift
  if "$@" >/dev/null 2>&1; then
    record_ok "${check_name}"
  else
    record_failure "${check_name}"
  fi
}

check_not_empty() {
  local var_name="$1"
  local var_value="${!var_name:-}"
  if [[ -n "${var_value}" ]]; then
    record_ok "env:${var_name}"
  else
    record_failure "env:${var_name}"
  fi
}

echo "== Social Agent Predeploy Check =="
echo "deploy.env: ${DEPLOY_ENV_FILE}"

for required in PROJECT_ID CONFIRM_PROJECT_ID REGION SERVICE_NAME; do
  check_not_empty "${required}"
done

if [[ "${PROJECT_ID:-}" != "${CONFIRM_PROJECT_ID:-}" ]]; then
  record_failure "env:CONFIRM_PROJECT_ID_matches_PROJECT_ID"
else
  record_ok "env:CONFIRM_PROJECT_ID_matches_PROJECT_ID"
fi

X_EXECUTION_MODE="${X_EXECUTION_MODE:-operator}"
if [[ "${X_EXECUTION_MODE}" != "api" && "${X_EXECUTION_MODE}" != "operator" ]]; then
  record_failure "env:X_EXECUTION_MODE_valid(api|operator)"
else
  record_ok "env:X_EXECUTION_MODE_valid(api|operator)"
fi

if [[ "${PROJECT_ID:-}" == "your-new-gcp-project-id" ]]; then
  record_failure "env:PROJECT_ID_not_template"
else
  record_ok "env:PROJECT_ID_not_template"
fi

if ! command -v gcloud >/dev/null 2>&1; then
  record_failure "gcloud_installed"
else
  record_ok "gcloud_installed"
fi

ACTIVE_ACCOUNT="$(gcloud auth list --filter=status:ACTIVE --format='value(account)' | head -n1 || true)"
if [[ -z "${ACTIVE_ACCOUNT}" ]]; then
  record_failure "gcloud_active_account"
else
  record_ok "gcloud_active_account"
fi

if [[ -n "${PROJECT_ID:-}" ]]; then
  check_cmd "gcp_project_exists" gcloud projects describe "${PROJECT_ID}" --project "${PROJECT_ID}"
fi

SERVICE_ACCOUNT_NAME="${SERVICE_ACCOUNT_NAME:-social-agent-sa}"
SERVICE_ACCOUNT_EMAIL="${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
check_cmd "runtime_service_account_exists" gcloud iam service-accounts describe "${SERVICE_ACCOUNT_EMAIL}" --project "${PROJECT_ID}"

required_secret_names=(
  reddit-client-id
  reddit-client-secret
  reddit-username
  reddit-password
  meta-page-access-token
  meta-ig-user-id
  meta-app-secret
  meta-verify-token
  x-webhook-token
)

for secret_name in "${required_secret_names[@]}"; do
  check_cmd "secret:${secret_name}" gcloud secrets describe "${secret_name}" --project "${PROJECT_ID}"
done

optional_secret_names=(
  x-api-key
  x-api-secret
  x-access-secret
  x-bearer-token
)

if [[ "${X_EXECUTION_MODE}" == "api" ]]; then
  check_cmd "secret:x-access-token" gcloud secrets describe "x-access-token" --project "${PROJECT_ID}"
else
  if gcloud secrets describe "x-access-token" --project "${PROJECT_ID}" >/dev/null 2>&1; then
    record_ok "secret_optional:x-access-token"
  else
    record_warn "secret_optional_missing:x-access-token"
  fi
fi

for secret_name in "${optional_secret_names[@]}"; do
  if gcloud secrets describe "${secret_name}" --project "${PROJECT_ID}" >/dev/null 2>&1; then
    record_ok "secret_optional:${secret_name}"
  else
    record_warn "secret_optional_missing:${secret_name}"
  fi
done

REGION="${REGION:-us-central1}"
if gcloud run services describe "${SERVICE_NAME}" --project "${PROJECT_ID}" --region "${REGION}" >/dev/null 2>&1; then
  if [[ "${ALLOW_UPDATE_EXISTING_SERVICE:-0}" == "1" ]]; then
    record_ok "cloud_run_target_existing_update_allowed"
  else
    record_failure "cloud_run_target_existing_update_blocked"
  fi
else
  record_ok "cloud_run_target_new_service"
fi

echo "Running local behavioral E2E suite..."
if pytest -q "${REPO_ROOT}/tests/test_e2e_agent_behavior.py"; then
  record_ok "tests:test_e2e_agent_behavior"
else
  record_failure "tests:test_e2e_agent_behavior"
fi

if [[ "${RUN_LIVE_LLM_E2E}" == "1" ]]; then
  echo "Running live Vertex LLM E2E suite..."
  if RUN_E2E_LLM_TESTS=1 pytest -q "${REPO_ROOT}/tests/test_e2e_llm.py"; then
    record_ok "tests:test_e2e_llm_live"
  else
    record_failure "tests:test_e2e_llm_live"
  fi
else
  echo "Skipping live LLM E2E (set RUN_LIVE_LLM_E2E=1 to enable)."
fi

echo
if (( ${#failures[@]} == 0 )); then
  echo "PREDEPLOY CHECK: PASS"
  if (( ${#warnings[@]} > 0 )); then
    echo "Warnings (${#warnings[@]}):"
    printf ' - %s\n' "${warnings[@]}"
  fi
  exit 0
fi

echo "PREDEPLOY CHECK: FAIL (${#failures[@]} issue(s))"
printf ' - %s\n' "${failures[@]}"
exit 1
