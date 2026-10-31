#!/usr/bin/env bash
# Memulihkan database dari backup. MENIMPA isi database saat ini.
# Pakai: deploy/pulihkan.sh hydro-XXXX.dump.age kunci-age.txt
set -euo pipefail

berkas=${1:?berkas .dump.age}
kunci=${2:?berkas kunci age}

cd "$(dirname "$0")/.."
set -a; source .env; set +a

read -r -p "Timpa database $POSTGRES_DB? Ketik YA: " jawab
[ "$jawab" = "YA" ] || exit 1

docker compose stop api web
age -d -i "$kunci" "$berkas" \
  | docker compose exec -T db pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists --no-owner
docker compose up -d
echo "Pemulihan selesai. Cek aplikasi sebelum dipakai."
