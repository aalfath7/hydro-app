#!/usr/bin/env bash
# Rilis versi baru: deploy/rilis.sh 1.2.0
set -euo pipefail

versi=${1:?nomor versi}
cd "$(dirname "$0")/.."

bash deploy/backup.sh
sed -i "s/^APP_VERSION=.*/APP_VERSION=$versi/" .env
docker compose pull web api
docker compose run --rm api python manage.py migrate
docker compose up -d
echo "Versi $versi berjalan."
