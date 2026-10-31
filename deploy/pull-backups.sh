#!/bin/sh
# Copy the server's backups to this computer: a second place, in case the server is lost.
# Usage:  QB_HOST=ubuntu@<IP> QB_KEY=~/.ssh/qb_oracle ./deploy/pull-backups.sh
# On a Mac it can run daily with launchd: see docs/06-deploy-oracle.md, section 6.
set -eu
host="${QB_HOST:?set QB_HOST=ubuntu@<server IP>}"
key="${QB_KEY:-$HOME/.ssh/qb_oracle}"
dest="${QB_BACKUP_DEST:-$HOME/qb-backups}"
mkdir -p "$dest"
# No --delete: what was copied here stays even after the server drops it
rsync -az --include "*.gz" --exclude "*" -e "ssh -i $key -o BatchMode=yes -o ConnectTimeout=20" \
	"$host:qb-backups/" "$dest/"
echo "$(date '+%Y-%m-%d %H:%M') pulled into $dest: $(ls "$dest" | wc -l | tr -d ' ') files"
