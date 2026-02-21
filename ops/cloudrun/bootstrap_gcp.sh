#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
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

if [[ "${PROJECT_ID}" != "${CONFIRM_PROJECT_ID}" ]]; then
  echo "Safety stop: CONFIRM_PROJECT_ID must match PROJECT_ID."
  echo "PROJECT_ID=${PROJECT_ID}"
  echo "CONFIRM_PROJECT_ID=${CONFIRM_PROJECT_ID}"
  exit 1
fi

REGION="${REGION:-us-central1}"
ARTIFACT_REPO="${ARTIFACT_REPO:-social-agent}"
SERVICE_ACCOUNT_NAME="${SERVICE_ACCOUNT_NAME:-social-agent-sa}"
SERVICE_ACCOUNT_EMAIL="${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

ACTIVE_ACCOUNT="$(gcloud auth list --filter=status:ACTIVE --format='value(account)' | head -n1 || true)"
if [[ -z "${ACTIVE_ACCOUNT}" ]]; then
  echo "No active gcloud account. Run: gcloud auth login"
  exit 1
fi

echo "Using gcloud account: ${ACTIVE_ACCOUNT}"
echo "Using project: ${PROJECT_ID}"
PROJECT_NUMBER="$(gcloud projects describe "${PROJECT_ID}" --project "${PROJECT_ID}" --format='value(projectNumber)')"

echo "Enabling required APIs..."
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  secretmanager.googleapis.com \
  logging.googleapis.com \
  monitoring.googleapis.com \
  --project "${PROJECT_ID}" >/dev/null

if gcloud artifacts repositories describe "${ARTIFACT_REPO}" --location "${REGION}" --project "${PROJECT_ID}" >/dev/null 2>&1; then
  echo "Artifact Registry exists: ${ARTIFACT_REPO}"
else
  echo "Creating Artifact Registry: ${ARTIFACT_REPO}"
  gcloud artifacts repositories create "${ARTIFACT_REPO}" \
    --repository-format=docker \
    --location="${REGION}" \
    --description="Social Agent container images" \
    --project "${PROJECT_ID}" >/dev/null
fi

if gcloud iam service-accounts describe "${SERVICE_ACCOUNT_EMAIL}" --project "${PROJECT_ID}" >/dev/null 2>&1; then
  echo "Service account exists: ${SERVICE_ACCOUNT_EMAIL}"
else
  echo "Creating service account: ${SERVICE_ACCOUNT_EMAIL}"
  gcloud iam service-accounts create "${SERVICE_ACCOUNT_NAME}" \
    --display-name="Social Agent Runtime Service Account" \
    --project "${PROJECT_ID}" >/dev/null
fi

echo "Applying IAM roles to runtime service account..."
for role in \
  roles/secretmanager.secretAccessor \
  roles/logging.logWriter \
  roles/monitoring.metricWriter \
  roles/aiplatform.user; do
  gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
    --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
    --role="${role}" \
    --quiet >/dev/null
done

echo "Applying Artifact Registry writer role to build service accounts when present..."
for build_sa in \
  "${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" \
  "${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"; do
  if gcloud iam service-accounts describe "${build_sa}" --project "${PROJECT_ID}" >/dev/null 2>&1; then
    gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
      --member="serviceAccount:${build_sa}" \
      --role="roles/artifactregistry.writer" \
      --quiet >/dev/null
    echo "Granted roles/artifactregistry.writer to ${build_sa}"
  else
    echo "Skipped missing build service account: ${build_sa}"
  fi
done

echo "Bootstrap complete."
echo "Next step: ${SCRIPT_DIR}/sync_secrets.sh ${DEPLOY_ENV_FILE} ${SCRIPT_DIR}/secrets.env"
