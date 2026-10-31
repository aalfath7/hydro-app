#!/usr/bin/env bash
# Backup harian: dump database dan foto, dienkripsi, lalu dikirim ke luar VPS.
# Contoh cron: 0 19 * * * cd /opt/hydro && bash deploy/backup.sh >> /var/log/hydro-backup.log 2>&1
set -euo pipefail

cd "$(dirname "$0")/.."
set -a; source .env; set +a

waktu=$(date -u +%Y%m%dT%H%M%SZ)
sementara=$(mktemp -d)
trap 'rm -rf "$sementara"' EXIT

docker compose exec -T db pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc \
  | age -r "$BACKUP_AGE_RECIPIENT" > "$sementara/hydro-$waktu.dump.age"

docker compose exec -T api tar -C /data -cf - media \
  | age -r "$BACKUP_AGE_RECIPIENT" > "$sementara/hydro-$waktu.media.tar.age"

test -s "$sementara/hydro-$waktu.dump.age"
rclone copy "$sementara" "$BACKUP_RCLONE_TUJUAN"
echo "$(date -Is) backup $waktu terkirim"
