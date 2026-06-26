#!/usr/bin/env bash
#
# Deploy the VisualSprint control plane + all downstream services to Cloud Run.
# Reads non-secret config from .env and injects secret values from Secret Manager.
#
# Prereqs (one-time) — see docs/DEPLOY.md:
#   gcloud auth login && gcloud config set project visualsprint-agent
#   gcloud services enable run.googleapis.com aiplatform.googleapis.com \
#       secretmanager.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com
#   printf '%s' 'ENCODED_BACKEND_KEY' | gcloud secrets create elastic-backend-key --data-file=-
#   printf '%s' 'ENCODED_MCP_KEY'     | gcloud secrets create elastic-mcp-key     --data-file=-
#   gsutil mb -l us-west1 gs://visualsprint-capture-media
#
# Then: cp .env.example .env, fill the REPLACE_* values, and run: bash deploy.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
set -a
# shellcheck disable=SC1090
source "${SCRIPT_DIR}/.env"
set +a

: "${PROJECT_ID:?set PROJECT_ID in .env}"
: "${REGION:?set REGION in .env}"

ELASTIC_BACKEND_SECRET="${ELASTIC_BACKEND_SECRET:-elastic-backend-key}"
ELASTIC_MCP_SECRET="${ELASTIC_MCP_SECRET:-elastic-mcp-key}"
JIRA_TOKEN_SECRET="${JIRA_TOKEN_SECRET:-}"
SLACK_TOKEN_SECRET="${SLACK_TOKEN_SECRET:-}"

echo ">> [0/5] Ensuring downstream service accounts exist ..."
ensure_service_account() {
  local sa_name=$1
  local sa_email="${sa_name}@${PROJECT_ID}.iam.gserviceaccount.com"
  if ! gcloud iam service-accounts describe "${sa_email}" --project "${PROJECT_ID}" >/dev/null 2>&1; then
    gcloud iam service-accounts create "${sa_name}" --project "${PROJECT_ID}" --display-name "${sa_name}"
  fi
}

ensure_service_account visualsprint-ingest
ensure_service_account visualsprint-media
ensure_service_account visualsprint-agents

echo ">> [1/5] Deploying visualsprint-api ..."
API_SECRETS="ELASTICSEARCH_API_KEY=${ELASTIC_BACKEND_SECRET}:latest"
[[ -n "${JIRA_TOKEN_SECRET}" ]] && API_SECRETS="${API_SECRETS},JIRA_API_TOKEN_SECRET=${JIRA_TOKEN_SECRET}:latest"
[[ -n "${SLACK_TOKEN_SECRET}" ]] && API_SECRETS="${API_SECRETS},SLACK_BOT_TOKEN_SECRET=${SLACK_TOKEN_SECRET}:latest"

gcloud run deploy visualsprint-api \
  --source services/api \
  --project "${PROJECT_ID}" \
  --region "${REGION}" \
  --allow-unauthenticated \
  --set-env-vars "^##^VISUALSPRINT_ENV=${VISUALSPRINT_ENV}##VISUALSPRINT_TRACK=${VISUALSPRINT_TRACK}##ELASTICSEARCH_URL=${ELASTICSEARCH_URL}##ELASTIC_INDEX_OUTCOMES=${ELASTIC_INDEX_OUTCOMES}##ELASTIC_MCP_SERVER_URL=${ELASTIC_MCP_SERVER_URL}##JIRA_BASE_URL=${JIRA_BASE_URL}##SLACK_DEFAULT_CHANNEL=${SLACK_DEFAULT_CHANNEL}##VISUALSPRINT_ALLOWED_ORIGINS=${VISUALSPRINT_ALLOWED_ORIGINS}" \
  --set-secrets "${API_SECRETS}"

API_URL="$(gcloud run services describe visualsprint-api --project "${PROJECT_ID}" --region "${REGION}" --format='value(status.url)')"
echo ">> control plane: ${API_URL}"

echo ">> [2/5] Deploying visualsprint-ingest ..."
gcloud run deploy visualsprint-ingest \
  --source services/ingest \
  --project "${PROJECT_ID}" \
  --region "${REGION}" \
  --service-account visualsprint-ingest@${PROJECT_ID}.iam.gserviceaccount.com \
  --allow-unauthenticated \
  --set-env-vars "^##^VISUALSPRINT_ENV=${VISUALSPRINT_ENV}##VISUALSPRINT_TRACK=${VISUALSPRINT_TRACK}##GOOGLE_CLOUD_PROJECT=${GOOGLE_CLOUD_PROJECT}##GOOGLE_CLOUD_LOCATION=${GOOGLE_CLOUD_LOCATION}##GCS_BUCKET=${GCS_BUCKET}##GCS_SIGNED_URL_TTL_SECONDS=${GCS_SIGNED_URL_TTL_SECONDS}##SPEECH_LANGUAGE_CODE=${SPEECH_LANGUAGE_CODE}##SPEECH_ENABLE_SPEAKER_DIARIZATION=${SPEECH_ENABLE_SPEAKER_DIARIZATION}##VISUALSPRINT_INGEST_REAL_PIPELINE_ENABLED=${VISUALSPRINT_INGEST_REAL_PIPELINE_ENABLED}"

INGEST_URL="$(gcloud run services describe visualsprint-ingest --project "${PROJECT_ID}" --region "${REGION}" --format='value(status.url)')"
echo ">> ingest: ${INGEST_URL}"

echo ">> [3/5] Deploying visualsprint-media ..."
gcloud run deploy visualsprint-media \
  --source services/media \
  --project "${PROJECT_ID}" \
  --region "${REGION}" \
  --service-account visualsprint-media@${PROJECT_ID}.iam.gserviceaccount.com \
  --allow-unauthenticated \
  --set-env-vars "^##^VISUALSPRINT_ENV=${VISUALSPRINT_ENV}##VISUALSPRINT_TRACK=${VISUALSPRINT_TRACK}##GOOGLE_CLOUD_PROJECT=${GOOGLE_CLOUD_PROJECT}##GOOGLE_CLOUD_LOCATION=${GOOGLE_CLOUD_LOCATION}##GCS_BUCKET=${GCS_BUCKET}##GEMINI_VISION_MODEL=${GEMINI_VISION_MODEL}##VISUALSPRINT_MEDIA_FRAME_INTERVAL_SECONDS=${VISUALSPRINT_MEDIA_FRAME_INTERVAL_SECONDS}##VISUALSPRINT_MEDIA_REAL_PIPELINE_ENABLED=${VISUALSPRINT_MEDIA_REAL_PIPELINE_ENABLED}"

MEDIA_URL="$(gcloud run services describe visualsprint-media --project "${PROJECT_ID}" --region "${REGION}" --format='value(status.url)')"
echo ">> media: ${MEDIA_URL}"

echo ">> [4/5] Deploying visualsprint-agents (control plane = ${API_URL}) ..."
gcloud run deploy visualsprint-agents \
  --source services/agents \
  --project "${PROJECT_ID}" \
  --region "${REGION}" \
  --service-account "${VISUALSPRINT_SERVICE_ACCOUNT_EMAIL}" \
  --allow-unauthenticated \
  --set-env-vars "^##^VISUALSPRINT_ENV=${VISUALSPRINT_ENV}##VISUALSPRINT_TRACK=${VISUALSPRINT_TRACK}##VISUALSPRINT_AGENT_MODE=${VISUALSPRINT_AGENT_MODE}##VISUALSPRINT_DEPLOYMENT_TARGET=${VISUALSPRINT_DEPLOYMENT_TARGET}##VISUALSPRINT_AGENT_RUNTIME_BACKEND=${VISUALSPRINT_AGENT_RUNTIME_BACKEND}##VISUALSPRINT_GOOGLE_CLOUD_PROJECT_ID=${VISUALSPRINT_GOOGLE_CLOUD_PROJECT_ID}##VISUALSPRINT_GOOGLE_CLOUD_PROJECT_NUMBER=${VISUALSPRINT_GOOGLE_CLOUD_PROJECT_NUMBER}##VISUALSPRINT_GOOGLE_CLOUD_LOCATION=${VISUALSPRINT_GOOGLE_CLOUD_LOCATION}##VISUALSPRINT_AGENT_APPLICATION_ID=${VISUALSPRINT_AGENT_APPLICATION_ID}##VISUALSPRINT_REASONING_ENGINE_RESOURCE_NAME=${VISUALSPRINT_REASONING_ENGINE_RESOURCE_NAME}##VISUALSPRINT_SUMMARY_ENGINE_RESOURCE_NAME=${VISUALSPRINT_SUMMARY_ENGINE_RESOURCE_NAME}##VISUALSPRINT_ACTION_ENGINE_RESOURCE_NAME=${VISUALSPRINT_ACTION_ENGINE_RESOURCE_NAME}##VISUALSPRINT_CONTROL_PLANE_URL=${API_URL}##VISUALSPRINT_ELASTIC_MCP_ENDPOINT=${VISUALSPRINT_ELASTIC_MCP_ENDPOINT}##VISUALSPRINT_REASONING_MODEL=${VISUALSPRINT_REASONING_MODEL}##VISUALSPRINT_SUMMARY_MODEL=${VISUALSPRINT_SUMMARY_MODEL}##VISUALSPRINT_ACTION_MODEL=${VISUALSPRINT_ACTION_MODEL}##VISUALSPRINT_ALLOWED_ORIGINS=${VISUALSPRINT_ALLOWED_ORIGINS}##VISUALSPRINT_AGENT_REQUEST_TIMEOUT_SECONDS=${VISUALSPRINT_AGENT_REQUEST_TIMEOUT_SECONDS}" \
  --set-secrets "VISUALSPRINT_ELASTIC_API_KEY=${ELASTIC_MCP_SECRET}:latest"

AGENTS_URL="$(gcloud run services describe visualsprint-agents --project "${PROJECT_ID}" --region "${REGION}" --format='value(status.url)')"
echo ">> agents: ${AGENTS_URL}"

echo ">> [5/5] Pointing control plane at downstream services ..."
gcloud run services update visualsprint-api \
  --project "${PROJECT_ID}" \
  --region "${REGION}" \
  --update-env-vars "VISUALSPRINT_AGENTS_SERVICE_URL=${AGENTS_URL}##VISUALSPRINT_INGEST_SERVICE_URL=${INGEST_URL}##VISUALSPRINT_MEDIA_SERVICE_URL=${MEDIA_URL}"

echo ">> Done. Validate:"
echo "   curl ${AGENTS_URL}/api/health"
echo "   curl ${API_URL}/api/meta"
echo "   curl -X POST ${API_URL}/api/meetings/MEETING_ID/agents/smoke?clientChunkId=CHUNK_ID"
echo "   curl ${API_URL}/api/meta/agents/invocations"
