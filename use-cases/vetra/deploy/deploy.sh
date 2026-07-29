#!/usr/bin/env bash
set -euo pipefail

echo "=== Vetra — AWS Lambda Deployment ==="
cd "$(dirname "$0")"

PROJECT_ROOT="$(dirname "$0")/.."

echo "[1/4] Exporting dependencies..."
cd "$PROJECT_ROOT"
uv export --format requirements-txt > deploy/requirements.txt
echo "✓ Requirements exported"

echo "[2/4] Building Docker image..."
cd deploy
docker build -t vetra-lambda .

echo "[3/4] Initializing Terraform..."
terraform init

echo "[4/4] Deploying..."
terraform apply -auto-approve

echo ""
echo "Deployment complete."
echo "Invoke URL: terraform output -raw agent_invoke_url"
