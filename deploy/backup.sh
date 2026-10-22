#!/bin/sh
# Daily backup of the database and uploaded files into ~/qb-backups (keeps 14 days).
# Cron:  0 3 * * *  cd ~/qb && ./deploy/backup.sh
set -eu
cd "$(dirname "$0")/.."
dir="${BACKUP_DIR:-$HOME/qb-backups}"
stamp="$(date +%Y%m%d-%H%M)"
mkdir -p "$dir"
docker compose -f docker-compose.prod.yml exec -T db pg_dump -U qb qb | gzip > "$dir/db-$stamp.sql.gz"
docker compose -f docker-compose.prod.yml exec -T api tar -C /app -czf - media > "$dir/media-$stamp.tar.gz"
find "$dir" -type f -mtime +14 -delete
echo "backup done: $dir ($stamp)"
